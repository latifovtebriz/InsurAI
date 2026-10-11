"""Transactional Outbox pattern implementation and idempotent event dispatcher."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.modules.platform.models import OutboxEvent, ProcessedEvent
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

EventHandler = Callable[[OutboxEvent], None]


class OutboxDispatcher:
    """Manages event subscriptions and dispatches pending outbox events idempotently."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[str, EventHandler]]] = {}

    def register_consumer(self, event_type: str, consumer_name: str, handler: EventHandler) -> None:
        """Registers an idempotent consumer for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((consumer_name, handler))

    def dispatch_pending(self, session: Session, batch_size: int = 50) -> int:
        """
        Fetches pending outbox events and dispatches them to registered consumers.
        Idempotency is guaranteed by tracking (event_id, consumer_name) pairs.
        """
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.created_at)
            .limit(batch_size)
        )
        events = session.scalars(stmt).all()
        dispatched_count = 0

        for event in events:
            handlers = self._handlers.get(event.event_type, [])
            all_succeeded = True

            for consumer_name, handler in handlers:
                # Idempotency check: has this consumer already processed this event?
                already_processed = session.get(
                    ProcessedEvent, {"event_id": event.id, "consumer_name": consumer_name}
                )
                if already_processed:
                    logger.info(
                        f"Skipping event '{event.id}' for consumer '{consumer_name}' (already processed)."
                    )
                    continue

                try:
                    handler(event)
                    # Record processed marker
                    record = ProcessedEvent(
                        event_id=event.id,
                        consumer_name=consumer_name,
                        processed_at=datetime.now(UTC),
                    )
                    session.add(record)
                except Exception as exc:
                    logger.error(
                        f"Handler '{consumer_name}' failed processing event '{event.id}': {exc}"
                    )
                    all_succeeded = False
                    event.error_message = str(exc)
                    event.retry_count += 1
                    break

            if all_succeeded:
                event.status = "published"
                event.published_at = datetime.now(UTC)
                dispatched_count += 1
            else:
                event.status = "failed" if event.retry_count >= 3 else "pending"

        session.commit()
        return dispatched_count


dispatcher = OutboxDispatcher()


def publish_outbox_event(
    session: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    """
    Writes an outbox event into the database within the current active transaction.
    Will commit or roll back atomically with business entity mutations.
    """
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
        status="pending",
    )
    session.add(event)
    return event

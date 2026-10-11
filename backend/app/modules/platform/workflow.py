"""Declarative state machine engine for insurance domain lifecycles."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class InvalidStateTransitionError(Exception):
    """Raised when an unauthorized or undefined state transition is attempted."""

    pass


class GuardConditionFailedError(Exception):
    """Raised when a transition guard rejects the transition."""

    pass


@dataclass
class Transition:
    from_state: str
    to_state: str
    trigger: str
    guard: Callable[[dict[str, Any]], bool] | None = None
    hook: Callable[[dict[str, Any]], None] | None = None


@dataclass
class StateMachineDefinition:
    name: str
    initial_state: str
    valid_states: set[str]
    transitions: list[Transition]

    def trigger(
        self, current_state: str, trigger_name: str, context: dict[str, Any] | None = None
    ) -> str:
        """Executes a transition if permitted, otherwise raises InvalidStateTransitionError."""
        ctx = context or {}

        if current_state not in self.valid_states:
            raise InvalidStateTransitionError(
                f"State '{current_state}' is not a valid state in workflow '{self.name}'"
            )

        matching = [
            t
            for t in self.transitions
            if t.from_state == current_state and t.trigger == trigger_name
        ]

        if not matching:
            raise InvalidStateTransitionError(
                f"Illegal transition in workflow '{self.name}': no transition from '{current_state}' "
                f"triggered by '{trigger_name}'."
            )

        trans = matching[0]

        # Check guard
        if trans.guard is not None and not trans.guard(ctx):
            raise GuardConditionFailedError(
                f"Transition from '{current_state}' to '{trans.to_state}' blocked by guard condition."
            )

        # Execute hook if registered
        if trans.hook is not None:
            trans.hook(ctx)

        return trans.to_state


# ==============================================================================
# Declarative Workflow Definitions
# ==============================================================================

QUOTE_WORKFLOW = StateMachineDefinition(
    name="quote",
    initial_state="draft",
    valid_states={"draft", "quoted", "underwriting_review", "bound", "declined", "expired"},
    transitions=[
        Transition("draft", "quoted", "calculate_quote"),
        Transition("quoted", "underwriting_review", "refer_underwriting"),
        Transition("underwriting_review", "quoted", "approve_referral"),
        Transition("underwriting_review", "declined", "decline_referral"),
        Transition("quoted", "bound", "bind_quote"),
        Transition("quoted", "expired", "expire_quote"),
    ],
)

POLICY_WORKFLOW = StateMachineDefinition(
    name="policy",
    initial_state="bound",
    valid_states={"bound", "pending_payment", "active", "cancelled", "expired", "renewed"},
    transitions=[
        Transition("bound", "pending_payment", "issue_invoice"),
        Transition("pending_payment", "active", "confirm_payment"),
        Transition("pending_payment", "cancelled", "cancel_policy"),
        Transition("active", "cancelled", "cancel_policy"),
        Transition("active", "expired", "expire_policy"),
        Transition("active", "renewed", "renew_policy"),
    ],
)

CLAIM_WORKFLOW = StateMachineDefinition(
    name="claim",
    initial_state="fnol_received",
    valid_states={
        "fnol_received",
        "registered",
        "triage_in_progress",
        "awaiting_review",
        "approved",
        "rejected",
        "settled",
        "closed",
    },
    transitions=[
        Transition("fnol_received", "registered", "register_claim"),
        Transition("registered", "triage_in_progress", "start_triage"),
        Transition("triage_in_progress", "awaiting_review", "submit_recommendation"),
        Transition("awaiting_review", "approved", "confirm_approval"),
        Transition("awaiting_review", "rejected", "confirm_rejection"),
        Transition("approved", "settled", "disburse_payment"),
        Transition("settled", "closed", "close_claim"),
        Transition("rejected", "closed", "close_claim"),
    ],
)

INVOICE_WORKFLOW = StateMachineDefinition(
    name="invoice",
    initial_state="pending",
    valid_states={"pending", "paid", "overdue", "cancelled"},
    transitions=[
        Transition("pending", "paid", "receive_payment"),
        Transition("pending", "overdue", "mark_overdue"),
        Transition("overdue", "paid", "receive_payment"),
        Transition("pending", "cancelled", "cancel_invoice"),
        Transition("overdue", "cancelled", "cancel_invoice"),
    ],
)

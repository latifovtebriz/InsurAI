"""Hand-written ReAct agent runtime loop with budgets, loop detection, and guardrails."""

import hashlib
import json
import logging
import time
import uuid
from typing import Any

from app.config import settings
from app.modules.platform.llm.client import LLMMessage
from app.modules.platform.llm.gateway import LLMGateway, gateway
from app.modules.platform.runtime.guardrails import GuardrailPipeline, guardrail_pipeline
from app.modules.platform.runtime.models import AgentRun, AgentStep
from app.modules.platform.runtime.tools import ToolCategory, ToolRegistry
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AgentLoop:
    """Hand-written ReAct loop ensuring determinism, safety bounds, and step-level tracing."""

    def __init__(
        self,
        agent_id: str,
        tool_registry: ToolRegistry,
        llm_gateway: LLMGateway | None = None,
        pipeline: GuardrailPipeline | None = None,
        max_steps: int | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.registry = tool_registry
        self.gateway = llm_gateway or gateway
        self.pipeline = pipeline or guardrail_pipeline
        self.max_steps = max_steps or settings.agent_max_steps

    async def run(
        self,
        session: Session | None,
        system_prompt: str,
        initial_user_message: str,
        correlation_id: str | None = None,
        input_payload: dict[str, Any] | None = None,
        raw_text_inputs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Executes the agent loop until terminal tool submission or budget exhaustion."""
        corr_id = correlation_id or str(uuid.uuid4())
        run_record = AgentRun(
            agent_id=self.agent_id,
            correlation_id=corr_id,
            input_payload=input_payload or {"prompt": initial_user_message},
            status="running",
        )
        if session:
            session.add(run_record)
            session.commit()

        start_time = time.time()
        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=initial_user_message),
        ]

        step_count = 0
        total_tokens = 0
        total_cost = 0.0
        consecutive_tool_history: list[str] = []
        executed_tool_calls: list[dict[str, Any]] = []
        retrieved_clauses: list[str] = []
        final_output: dict[str, Any] = {
            "recommendation": "needs_human_review",
            "confidence": 0.0,
            "summary": "Agent session terminated before reaching conclusion.",
            "reasons": [{"type": "risk", "statement": "Session budget or timeout reached."}],
        }

        while step_count < self.max_steps:
            step_count += 1
            step_start = time.time()

            try:
                # 1. Call LLM
                declarations = self.registry.to_declarations()
                resp = await self.gateway.generate(
                    messages=messages,
                    temperature=0.0,
                    tools=declarations,
                )
                total_tokens += resp.total_tokens
                total_cost += resp.cost_estimate

                # Trace LLM step
                llm_latency = int((time.time() - step_start) * 1000)
                if session:
                    session.add(
                        AgentStep(
                            run_id=run_record.id,
                            step_index=step_count,
                            step_kind="llm_call",
                            tokens_used=resp.total_tokens,
                            latency_ms=llm_latency,
                        )
                    )
                    session.commit()

                # Check if model invoked tools
                # In Fake/mock mode or real mode: inspect content for tool call markers or structured output
                tool_call = self._parse_tool_call(resp.content)

                if not tool_call:
                    # Model provided text without tool call; conclude session
                    final_output["summary"] = resp.content
                    break

                tool_name = tool_call["name"]
                tool_args = tool_call["arguments"]

                # 2. Loop Detection (consecutive identical tool calls)
                call_hash = f"{tool_name}:{hashlib.sha256(json.dumps(tool_args, sort_keys=True).encode()).hexdigest()}"
                consecutive_tool_history.append(call_hash)
                if (
                    len(consecutive_tool_history) >= 3
                    and consecutive_tool_history[-1]
                    == consecutive_tool_history[-2]
                    == consecutive_tool_history[-3]
                ):
                    logger.warning(
                        f"Loop detector triggered: 3 identical calls to '{tool_name}'. Terminating."
                    )
                    final_output = {
                        "recommendation": "needs_human_review",
                        "confidence": 0.0,
                        "summary": "Infinite tool execution loop detected.",
                        "reasons": [
                            {
                                "type": "risk",
                                "statement": f"Loop detector stopped repetitive calls to {tool_name}.",
                            }
                        ],
                    }
                    break

                # 3. Execute Tool
                tool_def = self.registry.get(tool_name)
                tool_res = self.registry.execute(tool_name, tool_args)
                executed_tool_calls.append(
                    {"tool_name": tool_name, "args": tool_args, "output": tool_res}
                )

                # If knowledge search was called, record retrieved clause IDs
                if tool_name == "search_policy_wording":
                    if isinstance(tool_res, list):
                        retrieved_clauses.extend(
                            c.get("clause_id") for c in tool_res if isinstance(c, dict)
                        )
                    elif "citations" in tool_res:
                        retrieved_clauses.extend(c.get("clause_id") for c in tool_res["citations"])

                # Trace tool step
                if session:
                    session.add(
                        AgentStep(
                            run_id=run_record.id,
                            step_index=step_count,
                            step_kind="tool_call",
                            tool_name=tool_name,
                            tool_input=tool_args,
                            tool_output=tool_res,
                            latency_ms=int((time.time() - step_start) * 1000),
                        )
                    )
                    session.commit()

                # 4. Check if Terminal Tool
                if tool_def and tool_def.category == ToolCategory.TERMINAL:
                    raw_rec = tool_args.get("recommendation", tool_args)

                    # Intercept with Guardrail Pipeline
                    guardrail_results = self.pipeline.evaluate_all(
                        recommendation=raw_rec,
                        executed_tool_calls=executed_tool_calls,
                        retrieved_clauses=retrieved_clauses,
                        raw_text_inputs=raw_text_inputs,
                    )

                    # Trace guardrail step
                    if session:
                        session.add(
                            AgentStep(
                                run_id=run_record.id,
                                step_index=step_count + 1,
                                step_kind="guardrail",
                                tool_name="guardrail_pipeline",
                                tool_output={"results": [g.__dict__ for g in guardrail_results]},
                            )
                        )
                        session.commit()

                    # Apply downgrades if any guardrail failed
                    downgrades = [g for g in guardrail_results if g.downgrade_to_review]
                    if downgrades:
                        raw_rec["recommendation"] = "needs_human_review"
                        for d in downgrades:
                            raw_rec.setdefault("reasons", []).append(
                                {
                                    "type": "risk",
                                    "statement": d.reason,
                                }
                            )

                    final_output = raw_rec
                    break

                # Append tool result to dialogue
                messages.append(
                    LLMMessage(
                        role="assistant", content=f"ToolCall: {tool_name}({json.dumps(tool_args)})"
                    )
                )
                messages.append(
                    LLMMessage(role="tool", content=json.dumps(tool_res), name=tool_name)
                )

            except Exception as exc:
                logger.exception(f"Unhandled error during agent step {step_count}: {exc}")
                final_output = {
                    "recommendation": "needs_human_review",
                    "confidence": 0.0,
                    "summary": f"Agent encountered unhandled exception: {exc}",
                    "reasons": [{"type": "risk", "statement": "Fail-safe safeguard engaged."}],
                }
                break

        # Finalize run
        elapsed = round(time.time() - start_time, 2)
        final_status = (
            "completed" if final_output.get("recommendation") == "approve" else "needs_human_review"
        )
        run_record.status = final_status
        run_record.final_output = final_output
        run_record.step_count = step_count
        run_record.total_tokens = total_tokens
        run_record.total_cost_usd = total_cost
        run_record.duration_seconds = elapsed
        if session:
            session.commit()

        return final_output

    def _parse_tool_call(self, content: str) -> dict[str, Any] | None:
        """Parses tool calls from JSON or tool syntax."""
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
                return parsed
            if isinstance(parsed, dict) and "tool" in parsed:
                return {"name": parsed["tool"], "arguments": parsed.get("parameters", {})}
        except Exception:
            pass

        # Regex fallback for `ToolCall: name(args)` syntax
        import re

        match = re.search(r"ToolCall:\s*([a-zA-Z0-9_]+)\((.*)\)", content)
        if match:
            tool_name = match.group(1)
            raw_args = match.group(2)
            try:
                args = json.loads(raw_args)
            except Exception:
                args = {}
            return {"name": tool_name, "arguments": args}

        return None

"""LLM client interfaces, Fake client, Record-and-Replay, and Gemini integration."""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate: float
    model_name: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for provider-agnostic LLM communication."""

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        response_schema: type[BaseModel] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Generates an LLM response from message history."""
        ...


class FakeLLMClient:
    """
    Deterministic offline fake LLM client for testing and evaluation plumbing.
    Produces schema-compliant structured outputs or scripted tool calls.
    """

    def __init__(self, default_model: str = "fake-gemini-2.0-flash") -> None:
        self.default_model = default_model
        self.call_count = 0
        self.custom_responses: dict[str, str] = {}

    def set_response_for_keyword(self, keyword: str, json_text: str) -> None:
        """Sets a pre-canned response if prompt contains keyword."""
        self.custom_responses[keyword] = json_text

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        response_schema: type[BaseModel] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        self.call_count += 1
        full_prompt = "\n".join(m.content for m in messages)

        # Check for pre-canned custom responses
        for kw, resp in self.custom_responses.items():
            if kw in full_prompt:
                return self._build_response(resp, self.default_model)

        # Handle Claims Triage Agent A4 multi-step ReAct flow in offline mode
        if tools and "Triage Claim:" in full_prompt:
            if "ToolCall: check_policy_active" not in full_prompt:
                pol_match = re.search(r"Policy Number:\s*([A-Z0-9-]+)", full_prompt)
                pol = pol_match.group(1) if pol_match else "POL-2026-MOD-0001"
                inc_match = re.search(r"Incident Date:\s*([0-9-]+)", full_prompt)
                inc = inc_match.group(1) if inc_match else "2026-06-01"
                return self._build_response(
                    f'Thought: I must verify if the policy was active on the date of loss.\nAction: check_policy_active\nAction Input: {{"policy_number": "{pol}", "incident_date": "{inc}"}}',
                    self.default_model,
                )
            if "ToolCall: calculate_payout" not in full_prompt:
                amt_match = re.search(r"Claimed Amount:\s*(\d+(?:\.\d+)?)", full_prompt)
                amt = float(amt_match.group(1)) if amt_match else 1000.0
                return self._build_response(
                    f'Thought: Policy is verified active. Now I compute the deterministic payout using calculate_payout.\nAction: calculate_payout\nAction Input: {{"claimed_amount": {amt}, "sum_insured": 38000.0, "deductible": 200.0}}',
                    self.default_model,
                )
            amt_match = re.search(r"Claimed Amount:\s*(\d+(?:\.\d+)?)", full_prompt)
            amt = float(amt_match.group(1)) if amt_match else 1000.0
            payable = max(0.0, amt - 200.0)
            rec = {
                "recommendation": "approve",
                "confidence": 0.95,
                "reasoning": "Policy active, partial damage verified, deductible 200 AZN applied deterministically.",
                "payout": {
                    "claimed_amount": amt,
                    "covered_loss": amt,
                    "deductible": 200.0,
                    "payable": payable,
                    "is_total_loss": False,
                    "salvage_deduction": 0.0,
                    "calculation_rule": "Standard Partial Loss: Claimed - Deductible",
                },
                "risk_flags": [],
                "missing_information": [],
                "clause_citations": [
                    {
                        "clause_id": "MOTOR_OD:A.1",
                        "section": "A",
                        "title": "Accidental Collision Damage",
                        "relevance": 0.95,
                    }
                ],
            }
            return self._build_response(
                f'Thought: All evidence gathered. Submitting terminal recommendation.\nAction: submit_recommendation\nAction Input: {{"recommendation": {json.dumps(rec)}}}',
                self.default_model,
            )

        # Handle Extraction Service request with Pydantic target schema
        if response_schema and response_schema.__name__ == "ExtractedClaim":
            extracted_json = self._extract_claim_fields_heuristically(full_prompt)
            return self._build_response(extracted_json, self.default_model)

        # Default fallback JSON if schema requested
        if response_schema:
            sample = response_schema.model_construct()
            return self._build_response(sample.model_dump_json(), self.default_model)

        # Default plain text response
        return self._build_response("Acknowledged by InsurAI Fake LLM.", self.default_model)

    def _extract_claim_fields_heuristically(self, text: str) -> str:
        """Deterministic heuristic extractor for offline fake client testing."""
        # Policy number pattern: POL-2026-M-0012 or similar
        pol_match = re.search(r"POL-[A-Z0-9-]+", text)
        pol_num = pol_match.group(0) if pol_match else None

        # Amount pattern: e.g. Claimed Amount: 1200 AZN or 1500.0 AZN
        amt_match = re.search(
            r"(?:Claimed Amount:\s*|amount[:\s]*|repair[:\s]*)?(\d+(?:\.\d+)?)\s*(?:AZN|azn)",
            text,
            re.I,
        )
        if not amt_match:
            amt_match = re.search(r"Claimed Amount:\s*(\d+(?:\.\d+)?)", text, re.I)
        amount = float(amt_match.group(1)) if amt_match else None

        # Date pattern: YYYY-MM-DD
        date_match = re.search(r"\b(202[4-6]-\d{2}-\d{2})\b", text)
        inc_date = date_match.group(1) if date_match else None

        # Alcohol keywords
        has_alcohol = bool(
            re.search(r"(alcohol|drunk|intoxicated|ethanol|1\.\d\s*g/l)", text, re.I)
        )

        # Injection heuristic
        has_injection = bool(
            re.search(
                r"(ignore previous|you are now|system override|approve this claim)", text, re.I
            )
        )

        data = {
            "policy_number": pol_num,
            "incident_date": inc_date,
            "incident_type": "collision" if "collision" in text.lower() else "other",
            "incident_location": "Baku" if "baku" in text.lower() else None,
            "claimed_amount": amount,
            "stated_driver": "Rashad Aliyev" if "rashad" in text.lower() else None,
            "alcohol_involved": has_alcohol if has_alcohol else False,
            "driver_licensed": True,
            "police_report_filed": bool("police" in text.lower()),
            "description_summary": "Heuristically parsed incident description.",
            "has_injection_risk": has_injection,
            "confidence_score": 0.95 if pol_num and amount else 0.60,
        }
        return json.dumps(data)

    def _build_response(self, content: str, model_name: str) -> LLMResponse:
        prompt_toks = 150
        comp_toks = len(content) // 4
        total_toks = prompt_toks + comp_toks
        cost = (prompt_toks * 0.15 + comp_toks * 0.60) / 1_000_000.0
        return LLMResponse(
            content=content,
            prompt_tokens=prompt_toks,
            completion_tokens=comp_toks,
            total_tokens=total_toks,
            cost_estimate=cost,
            model_name=model_name,
        )


class RecordReplayLLMClient:
    """Record-and-Replay LLM client for offline reproducible test runs."""

    def __init__(self, inner_client: LLMClient, storage_dir: Path, mode: str = "replay") -> None:
        self.inner_client = inner_client
        self.storage_dir = storage_dir
        self.mode = mode  # "record" or "replay"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _hash_request(self, messages: list[LLMMessage], temperature: float) -> str:
        content_key = "|".join(f"{m.role}:{m.content}" for m in messages) + f"|t:{temperature}"
        return hashlib.sha256(content_key.encode("utf-8")).hexdigest()

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        response_schema: type[BaseModel] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        req_hash = self._hash_request(messages, temperature)
        record_file = self.storage_dir / f"{req_hash}.json"

        if self.mode == "replay":
            if record_file.exists():
                with open(record_file, encoding="utf-8") as f:
                    data = json.load(f)
                return LLMResponse(**data)
            # Fallback to inner client if record not found
            logger.warning(f"Replay cache miss for {req_hash}; falling back to inner client.")
            return await self.inner_client.generate(messages, temperature, response_schema, tools)

        # Record mode
        response = await self.inner_client.generate(messages, temperature, response_schema, tools)
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "content": response.content,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                    "cost_estimate": response.cost_estimate,
                    "model_name": response.model_name,
                    "tool_calls": response.tool_calls,
                },
                f,
                indent=2,
            )
        return response


class GeminiLLMClient:
    """
    Live Google GenAI / Gemini client.
    Status: UNVERIFIED AGAINST LIVE API (active when LLM_API_KEY is supplied).
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model_name = model_name

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        response_schema: type[BaseModel] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError(
                "GeminiLLMClient requires a non-empty LLM_API_KEY. System running in offline mode."
            )

        # Real Google Gemini API invocation using HTTP / REST to avoid unverified native C dependencies
        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        contents: list[dict[str, Any]] = []
        for m in messages:
            role = "user" if m.role in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }

        if response_schema:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

            result = resp.json()
            candidate = result.get("candidates", [{}])[0]
            text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            usage = result.get("usageMetadata", {})
            p_tok = usage.get("promptTokenCount", 100)
            c_tok = usage.get("candidatesTokenCount", len(text) // 4)
            total = usage.get("totalTokenCount", p_tok + c_tok)

            return LLMResponse(
                content=text,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                total_tokens=total,
                cost_estimate=(p_tok * 0.15 + c_tok * 0.60) / 1_000_000.0,
                model_name=self.model_name,
            )

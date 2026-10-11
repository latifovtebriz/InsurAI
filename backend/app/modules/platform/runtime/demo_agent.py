"""Demo agent exercising the hand-written runtime loop and tool registry."""

from typing import Any

from app.modules.platform.knowledge.service import knowledge_service
from app.modules.platform.llm.gateway import LLMGateway
from app.modules.platform.runtime.loop import AgentLoop
from app.modules.platform.runtime.tools import ToolCategory, ToolDefinition, ToolRegistry
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class SearchWordingArgs(BaseModel):
    query: str = Field(description="Search query for policy wording")
    product_code: str = Field(default="MOTOR_OD", description="Product code")
    incident_date: str = Field(default="2026-05-01", description="Date in force")


class SubmitAnswerArgs(BaseModel):
    clause_id: str
    explanation: str


class ClauseLookupAgent:
    """Simple demo agent exercising the ReAct loop and tool registry."""

    def __init__(self, session: Session, gateway: LLMGateway | None = None) -> None:
        self.session = session
        self.registry = ToolRegistry()

        # Tool 1: search_policy_wording (Read)
        def _search_handler(args: SearchWordingArgs) -> dict[str, Any]:
            citations = knowledge_service.search_policy_wording(
                session=self.session,
                query=args.query,
                product_code=args.product_code,
                incident_date=args.incident_date,
                top_k=3,
            )
            return {
                "citations": [
                    {"clause_id": c.clause_id, "title": c.title, "text": c.text[:100]}
                    for c in citations
                ]
            }

        self.registry.register(
            ToolDefinition(
                name="search_policy_wording",
                description="Searches active policy clauses by semantic similarity.",
                parameters_schema=SearchWordingArgs,
                category=ToolCategory.READ,
                handler=_search_handler,
            )
        )

        # Tool 2: submit_answer (Terminal)
        def _submit_handler(args: SubmitAnswerArgs) -> dict[str, Any]:
            return {
                "status": "submitted",
                "clause_id": args.clause_id,
                "explanation": args.explanation,
            }

        self.registry.register(
            ToolDefinition(
                name="submit_answer",
                description="Submits the identified clause.",
                parameters_schema=SubmitAnswerArgs,
                category=ToolCategory.TERMINAL,
                handler=_submit_handler,
            )
        )

        self.loop = AgentLoop(
            agent_id="A0_demo_clause_lookup",
            tool_registry=self.registry,
            llm_gateway=gateway,
            max_steps=5,
        )

    async def run(self, user_question: str) -> dict[str, Any]:
        system_prompt = (
            "You are the InsurAI Clause Lookup Assistant.\n"
            "Search policy wording using tool 'search_policy_wording', then submit answer via 'submit_answer'."
        )
        return await self.loop.run(
            session=self.session,
            system_prompt=system_prompt,
            initial_user_message=user_question,
        )

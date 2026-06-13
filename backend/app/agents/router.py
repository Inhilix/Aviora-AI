from enum import Enum


class AgentType(Enum):
    RULE_BASED = "rule"
    LLM        = "llm"
    SCHEDULER  = "scheduler"
    RAG        = "rag"


INTENT_MAP = {
    # Deterministic — no LLM
    "deadline_check":       AgentType.RULE_BASED,
    "document_checklist":   AgentType.RULE_BASED,
    "university_shortlist": AgentType.RULE_BASED,
    "profile_score":        AgentType.RULE_BASED,
    "application_status":   AgentType.RULE_BASED,
    # RAG — grounded context
    "visa_guidance":        AgentType.RAG,
    "country_requirements": AgentType.RAG,
    # Generative LLM
    "sop_draft":            AgentType.LLM,
    "mock_interview":       AgentType.LLM,
    "open_question":        AgentType.LLM,
}


async def route_request(
    intent: str,
    payload: dict,
    student_context: dict,
    celery_task,
):
    agent_type = INTENT_MAP.get(intent)
    if agent_type is None:
        raise ValueError(f"Unknown intent: {intent}")

    if agent_type == AgentType.LLM:
        # Dispatch to Celery queue — non-blocking
        task = celery_task.delay(intent, payload, student_context)
        return {"task_id": task.id, "status": "queued"}

    # Extend here as rule / RAG agents are implemented
    raise NotImplementedError(f"Agent {agent_type} not yet wired in router")

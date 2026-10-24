"""
Typed Graph State for MorphAPI V2 LangGraph Workflow
"""

from typing import Any, TypedDict


class WorkflowStateV2(TypedDict):
    prompt: str
    target_url: str
    name: str | None
    user_id: str
    
    # Ingestion & Intent
    intent: dict[str, Any]
    inspection_url: str
    raw_html: str
    intercepted_api: dict[str, Any] | None
    
    # Discovery & Proposal
    plan: dict[str, Any] | None
    extracted_data: list[dict[str, Any]] | None
    
    # Verification & Healing
    is_verified: bool
    validation_issues: list[str]
    turn: int
    max_turns: int
    status: str  # "INITIALIZING", "INSPECTING", "PROPOSING", "TESTING", "VERIFIED", "HEALING", "FAILED", "ACTIVE"
    error_message: str | None
    
    # Final Result
    final_response: dict[str, Any] | None

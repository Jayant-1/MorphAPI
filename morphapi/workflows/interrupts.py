"""
MorphAPI Workflow Human-in-the-Loop Interrupts
Handles pausing workflows for human approval or clarification and safely validates resumed inputs.
"""

import logging
from typing import Any
from pydantic import BaseModel, Field

from morphapi.schemas.errors import FailureCode, MorphApiError

logger = logging.getLogger("morphapi.interrupts")


class HumanApprovalResumeInput(BaseModel):
    approved: bool
    approver_id: str = Field(..., min_length=1)
    notes: str | None = None


class ClarificationResumeInput(BaseModel):
    selected_choice: str = Field(..., min_length=1)
    operator_id: str = Field(..., min_length=1)
    additional_guidance: str | None = None


def validate_human_approval_input(payload: dict[str, Any]) -> HumanApprovalResumeInput:
    """Validates human approval input as untrusted data."""
    try:
        return HumanApprovalResumeInput(**payload)
    except Exception as e:
        raise MorphApiError(
            FailureCode.APPROVAL_REQUIRED,
            f"Invalid approval payload: {e}",
        ) from e


def validate_clarification_input(payload: dict[str, Any]) -> ClarificationResumeInput:
    """Validates clarification response as untrusted data."""
    try:
        return ClarificationResumeInput(**payload)
    except Exception as e:
        raise MorphApiError(
            FailureCode.APPROVAL_REQUIRED,
            f"Invalid clarification payload: {e}",
        ) from e

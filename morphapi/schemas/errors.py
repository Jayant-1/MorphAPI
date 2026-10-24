"""
MorphAPI Error Codes and Error Models
Defines stable public error codes and exceptions shared across layers.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class FailureCode(str, Enum):
    # Network and Security
    SSRF_DETECTED = "SSRF_DETECTED"
    DISALLOWED_URL = "DISALLOWED_URL"
    DISALLOWED_REDIRECT = "DISALLOWED_REDIRECT"
    DNS_RESOLUTION_FAILED = "DNS_RESOLUTION_FAILED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    POLICY_REVIEW_REQUIRED = "POLICY_REVIEW_REQUIRED"

    # Browser Execution
    BROWSER_TIMEOUT = "BROWSER_TIMEOUT"
    BROWSER_NAVIGATION_ERROR = "BROWSER_NAVIGATION_ERROR"
    BROWSER_RESOURCE_ERROR = "BROWSER_RESOURCE_ERROR"

    # Extraction and Selectors
    SELECTOR_NOT_FOUND = "SELECTOR_NOT_FOUND"
    SELECTOR_AMBIGUOUS = "SELECTOR_AMBIGUOUS"
    SELECTOR_UNSAFE = "SELECTOR_UNSAFE"
    EMPTY_EXTRACTION = "EMPTY_EXTRACTION"

    # Validation
    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
    TYPE_COERCION_FAILED = "TYPE_COERCION_FAILED"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # Provider (NVIDIA NIM)
    NIM_CONFIG_ERROR = "NIM_CONFIG_ERROR"
    NIM_PREFLIGHT_FAILED = "NIM_PREFLIGHT_FAILED"
    NIM_RATE_LIMITED = "NIM_RATE_LIMITED"
    NIM_TIMEOUT = "NIM_TIMEOUT"
    NIM_AUTH_ERROR = "NIM_AUTH_ERROR"
    NIM_INFERENCE_ERROR = "NIM_INFERENCE_ERROR"

    # Workflow & Governance
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"
    VERSION_NOT_FOUND = "VERSION_NOT_FOUND"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    INVALID_CANDIDATE = "INVALID_CANDIDATE"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    RATE_LIMITED = "RATE_LIMITED"


class MorphApiError(Exception):
    """Base exception for MorphAPI domain errors."""
    def __init__(self, code: FailureCode, message: str, details: dict[str, Any] | None = None, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable


class SsrfSecurityError(MorphApiError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(FailureCode.SSRF_DETECTED, message, details=details, retryable=False)


class SourcePolicyBlockedError(MorphApiError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(FailureCode.POLICY_BLOCKED, message, details=details, retryable=False)


class BrowserExecutionError(MorphApiError):
    def __init__(self, code: FailureCode, message: str, details: dict[str, Any] | None = None, retryable: bool = True):
        super().__init__(code, message, details=details, retryable=retryable)


class NIMProviderError(MorphApiError):
    def __init__(self, code: FailureCode, message: str, details: dict[str, Any] | None = None, retryable: bool = False):
        super().__init__(code, message, details=details, retryable=retryable)


class SchemaValidationError(MorphApiError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(FailureCode.SCHEMA_VALIDATION_FAILED, message, details=details, retryable=False)


class BudgetExhaustedError(MorphApiError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(FailureCode.BUDGET_EXHAUSTED, message, details=details, retryable=False)


class ErrorResponse(BaseModel):
    error_code: FailureCode
    message: str
    endpoint_id: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)

"""
Typed configuration for MorphAPI.
Reads from environment variables with safe defaults.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field


class MorphApiSettings(BaseModel):
    # App & Database Settings
    app_name: str = Field(default="MorphAPI Gateway")
    environment: str = Field(
        default_factory=lambda: os.getenv("MORPHAPI_ENV", "development")
    )
    db_path: str = Field(
        default_factory=lambda: os.getenv("MORPHAPI_DB_PATH", os.getenv("DB_PATH", "./morphapi.db"))
    )
    default_tenant_id: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_TENANT_ID", "default_tenant")
    )

    # NVIDIA NIM Provider Settings
    nvidia_nim_base_url: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    )
    nvidia_nim_api_key: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_NIM_API_KEY", "")
    )
    nvidia_nim_model: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.2-11b-vision-instruct")
    )
    nvidia_nim_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("NVIDIA_NIM_TIMEOUT_SECONDS", "30.0"))
    )
    nvidia_nim_max_retries: int = Field(
        default_factory=lambda: int(os.getenv("NVIDIA_NIM_MAX_RETRIES", "1"))
    )

    # Playwright Settings
    playwright_headless: bool = Field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() in ("true", "1", "yes")
    )
    playwright_timeout_ms: int = Field(
        default_factory=lambda: int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "15000"))
    )
    playwright_navigation_timeout_ms: int = Field(
        default_factory=lambda: int(os.getenv("PLAYWRIGHT_NAVIGATION_TIMEOUT_MS", "20000"))
    )

    # Security & URL Policy
    allow_local_network: bool = Field(
        default_factory=lambda: os.getenv("URL_POLICY_ALLOW_LOCAL", "false").lower() in ("true", "1")
    )

    # Workflow & Budget Limits
    workflow_max_attempts: int = Field(
        default_factory=lambda: int(os.getenv("WORKFLOW_MAX_ATTEMPTS", "3"))
    )
    workflow_max_tool_calls: int = Field(
        default_factory=lambda: int(os.getenv("WORKFLOW_MAX_TOOL_CALLS", "10"))
    )
    workflow_deadline_seconds: float = Field(
        default_factory=lambda: float(os.getenv("WORKFLOW_DEADLINE_SECONDS", "120.0"))
    )
    per_tool_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("PER_TOOL_TIMEOUT_SECONDS", "15.0"))
    )

    # Checkpoint and Evidence Paths
    checkpoint_db_path: str = Field(
        default_factory=lambda: os.getenv("WORKFLOW_CHECKPOINT_DB_PATH", "morphapi_checkpoints.db")
    )
    evidence_dir: str = Field(
        default_factory=lambda: os.getenv("EVIDENCE_STORE_DIR", ".morphapi_evidence")
    )


settings = MorphApiSettings()

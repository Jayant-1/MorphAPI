"""
MorphAPI V2 Configuration
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Always load and override environment variables from .env
load_dotenv(override=True)


class MorphApiV2Settings(BaseModel):
    app_name: str = "MorphAPI V2 Gateway"
    environment: str = Field(default_factory=lambda: os.getenv("MORPHAPI_ENV", "development"))
    db_path: str = Field(default_factory=lambda: os.getenv("MORPHAPI_V2_DB_PATH", "./morphapi_v2.db"))
    
    # LLM Settings (NVIDIA NIM or OpenAI compatible)
    nvidia_nim_base_url: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    )
    nvidia_nim_api_key: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_NIM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    )
    nvidia_nim_model: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.2-11b-vision-instruct")
    )
    
    # Playwright Settings
    playwright_headless: bool = Field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() in ("true", "1", "yes")
    )
    playwright_timeout_ms: int = Field(default=30000)
    navigation_timeout_ms: int = Field(default=35000)
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    
    # DOM and cluster settings
    min_cluster_size: int = Field(default=2)
    min_diversity_ratio: float = Field(default=0.6)  # at least 60% unique values for titles/names
    min_coverage_ratio: float = Field(default=0.7)   # at least 70% non-null primary field


settings = MorphApiV2Settings()

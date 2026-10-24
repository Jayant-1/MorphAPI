"""
NVIDIA NIM / OpenAI-compatible LLM Client for MorphAPI V2
"""

import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import httpx
from morphapi_v2.config import settings

logger = logging.getLogger("morphapi_v2.nim")

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class NimClientV2:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self._override_api_key = api_key
        self._override_base_url = base_url
        self._override_model = model

    @property
    def api_key(self) -> str:
        if self._override_api_key:
            return self._override_api_key
        load_dotenv(dotenv_path=_ENV_PATH, override=True)
        return os.getenv("NVIDIA_NIM_API_KEY", os.getenv("OPENAI_API_KEY", settings.nvidia_nim_api_key))

    @property
    def base_url(self) -> str:
        if self._override_base_url:
            return self._override_base_url.rstrip("/")
        load_dotenv(dotenv_path=_ENV_PATH, override=True)
        return os.getenv("NVIDIA_NIM_BASE_URL", settings.nvidia_nim_base_url).rstrip("/")

    @property
    def model(self) -> str:
        if self._override_model:
            return self._override_model
        load_dotenv(dotenv_path=_ENV_PATH, override=True)
        return os.getenv("NVIDIA_NIM_MODEL", settings.nvidia_nim_model)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def generate_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: dict[str, str] | None = None,
    ) -> str:
        if not self.is_configured():
            raise RuntimeError("NVIDIA_NIM_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        # Removed restrictive 30s timeout: allow up to 120s for cloud inference
        client_timeout = httpx.Timeout(120.0, connect=30.0)
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"NIM provider error {resp.status_code}: {resp.text}")
            data = resp.json()
            choice = data["choices"][0]["message"]
            content = choice.get("content") or choice.get("reasoning_content") or ""
            return content


nim_client_v2 = NimClientV2()

# NVIDIA NIM + DeepSeek Provider Contract
MorphAPI uses NVIDIA NIM hosting or self-hosting, serving a DeepSeek model. Agent 4 owns the adapter; only healing calls it.

Hosted example configuration:
```env
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_API_KEY=replace_me
NVIDIA_NIM_MODEL=replace_with_enabled_multimodal_deepseek_model
NVIDIA_NIM_TIMEOUT_SECONDS=30
NVIDIA_NIM_MAX_RETRIES=1
```
For self-hosted NIM, use the deployment's base URL and auth arrangement. Confirm the exact model ID and image-input support in the current NVIDIA NIM catalog or `/v1/models`; a text-only model cannot accept the screenshot.

Install/pin the `openai` Python SDK. Example:
```python
import os
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url=os.environ["NVIDIA_NIM_BASE_URL"],
    api_key=os.environ["NVIDIA_NIM_API_KEY"],
    timeout=float(os.getenv("NVIDIA_NIM_TIMEOUT_SECONDS", "30")),
    max_retries=int(os.getenv("NVIDIA_NIM_MAX_RETRIES", "1")),
)

async def complete(messages):
    response = await client.chat.completions.create(
        model=os.environ["NVIDIA_NIM_MODEL"],
        messages=messages,
        max_tokens=2048,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""
```

For a multimodal user message, send content parts including text and an image, e.g. `{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}`. Confirm exact parameter names against the selected model's API reference.

Requirements:
- Fake model and real NIM adapter implement the same provider-neutral interface.
- Prompt for strict JSON with `new_selectors` and concise `ai_reasoning`.
- Treat page text as untrusted data, not instructions.
- Parse defensively; reject malformed or incomplete patches.
- Run Playwright extraction + Pydantic validation before persistence.
- Model client cannot write to SQLite.
- Log model ID, request ID, latency, outcome and token usage if available; never log credentials.
- Test text completion, image+text completion, invalid JSON, timeout, auth/rate limit, and no-persistence-on-failure.
- NIM is called only after the fast path fails.

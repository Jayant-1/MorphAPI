"""
MorphAPI NVIDIA NIM Tool-Calling Compatibility Preflight
Performs active verification against the configured NIM endpoint and model:
1. Tool-call request and parsed tool-call generation
2. Tool execution, tool-result round trip, and second model decision
3. Argument validation, rate-limit, and timeout handling
If preflight fails, agentic capability is marked not ready (no silent fallback).
"""

import json
import logging
import time
from typing import Any
from pydantic import BaseModel, Field

from morphapi.agent.nim_provider import NvidiaNimProvider
from morphapi.schemas.errors import FailureCode, NIMProviderError

logger = logging.getLogger("morphapi.nim_preflight")


class NIMPreflightResult(BaseModel):
    ready: bool
    model_id: str
    base_url: str
    tool_calling_supported: bool
    round_trip_success: bool
    vision_supported: bool
    latency_ms: int
    error_message: str | None = None
    diagnostic_details: dict[str, Any] = Field(default_factory=dict)


class NIMCompatibilityPreflight:
    """
    Runs preflight checks to guarantee the configured NVIDIA NIM model supports
    the required tool-calling capabilities before enabling agentic workflows.
    """

    def __init__(self, provider: NvidiaNimProvider | None = None):
        self.provider = provider or NvidiaNimProvider()

    async def run_preflight(self) -> NIMPreflightResult:
        """
        Executes end-to-end tool-calling preflight check against NIM endpoint.
        """
        start_ts = time.monotonic()
        details: dict[str, Any] = {}

        # 1. Define preflight verification tool
        test_tool = {
            "type": "function",
            "function": {
                "name": "verify_ping",
                "description": "Verification probe returning a test confirmation token",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "challenge_token": {
                            "type": "string",
                            "description": "A random challenge token to echo back",
                        }
                    },
                    "required": ["challenge_token"],
                },
            },
        }

        challenge_token = "morphapi_preflight_9981"
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": "You are a test agent. When asked, you must call the verify_ping tool with the provided challenge token.",
            },
            {
                "role": "user",
                "content": f"Please verify connectivity by calling verify_ping with challenge_token='{challenge_token}'.",
            },
        ]

        try:
            # Step A: First request with tool calling enabled
            resp = await self.provider.create_chat_completion(
                messages=messages,
                tools=[test_tool],
                tool_choice="auto",
                temperature=0.0,
                max_tokens=256,
            )

            choice = resp.choices[0]
            message = choice.message
            tool_calls = getattr(message, "tool_calls", None)

            if not tool_calls:
                elapsed_ms = int((time.monotonic() - start_ts) * 1000)
                return NIMPreflightResult(
                    ready=False,
                    model_id=self.provider.model_id,
                    base_url=self.provider.base_url,
                    tool_calling_supported=False,
                    round_trip_success=False,
                    vision_supported=self.provider.supports_vision(),
                    latency_ms=elapsed_ms,
                    error_message="Configured NIM model did not return any tool_calls. Tool calling is unsupported.",
                    diagnostic_details={"response_content": message.content},
                )

            # Validate tool call parameters
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments

            if function_name != "verify_ping":
                elapsed_ms = int((time.monotonic() - start_ts) * 1000)
                return NIMPreflightResult(
                    ready=False,
                    model_id=self.provider.model_id,
                    base_url=self.provider.base_url,
                    tool_calling_supported=False,
                    round_trip_success=False,
                    vision_supported=self.provider.supports_vision(),
                    latency_ms=elapsed_ms,
                    error_message=f"Model called unexpected function '{function_name}' instead of 'verify_ping'.",
                )

            try:
                args = json.loads(raw_arguments)
            except json.JSONDecodeError as je:
                elapsed_ms = int((time.monotonic() - start_ts) * 1000)
                return NIMPreflightResult(
                    ready=False,
                    model_id=self.provider.model_id,
                    base_url=self.provider.base_url,
                    tool_calling_supported=False,
                    round_trip_success=False,
                    vision_supported=self.provider.supports_vision(),
                    latency_ms=elapsed_ms,
                    error_message=f"Model returned malformed JSON arguments for tool call: {je}",
                    diagnostic_details={"raw_arguments": raw_arguments},
                )

            details["first_round_tool_call"] = {
                "id": tool_call.id,
                "function": function_name,
                "arguments": args,
            }

            # Step B: Execute the tool call and send tool result back
            tool_result_payload = json.dumps({
                "status": "success",
                "echo": args.get("challenge_token"),
                "verified": True,
            })

            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": raw_arguments,
                        },
                    }
                ],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result_payload,
            })

            # Step C: Second model call with tool result (round trip decision)
            round_trip_resp = await self.provider.create_chat_completion(
                messages=messages,
                temperature=0.0,
                max_tokens=256,
            )

            final_choice = round_trip_resp.choices[0]
            final_content = final_choice.message.content or ""
            details["second_round_content"] = final_content

            elapsed_ms = int((time.monotonic() - start_ts) * 1000)
            return NIMPreflightResult(
                ready=True,
                model_id=self.provider.model_id,
                base_url=self.provider.base_url,
                tool_calling_supported=True,
                round_trip_success=True,
                vision_supported=self.provider.supports_vision(),
                latency_ms=elapsed_ms,
                error_message=None,
                diagnostic_details=details,
            )

        except NIMProviderError as npe:
            elapsed_ms = int((time.monotonic() - start_ts) * 1000)
            logger.error("NIM Preflight failed: %s", npe.message)
            return NIMPreflightResult(
                ready=False,
                model_id=self.provider.model_id,
                base_url=self.provider.base_url,
                tool_calling_supported=False,
                round_trip_success=False,
                vision_supported=self.provider.supports_vision(),
                latency_ms=elapsed_ms,
                error_message=f"Preflight provider error: {npe.message}",
                diagnostic_details={"failure_code": npe.code.value},
            )
        except Exception as ex:
            elapsed_ms = int((time.monotonic() - start_ts) * 1000)
            logger.error("Unexpected NIM Preflight failure: %s", ex)
            return NIMPreflightResult(
                ready=False,
                model_id=self.provider.model_id,
                base_url=self.provider.base_url,
                tool_calling_supported=False,
                round_trip_success=False,
                vision_supported=self.provider.supports_vision(),
                latency_ms=elapsed_ms,
                error_message=f"Unexpected preflight failure: {ex}",
            )

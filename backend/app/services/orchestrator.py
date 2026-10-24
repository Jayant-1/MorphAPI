"""
MorphAPI Unified Extraction Orchestrator
Shared core extraction engine used identically by REST API and MCP Server.
Guarantees dual-path execution: Zero-token Fast Path first; LangGraph Agentic Healing on failure.
"""

import logging
import time
from typing import Any

from backend.app.database import get_endpoint, record_telemetry
from backend.app.models.contracts import ExtractionResponse
from backend.app.services.extraction import PlaywrightExtractionService
from backend.app.services.healer_graph import LangGraphHealingEngine
from backend.app.services.telemetry import telemetry_hub

logger = logging.getLogger("morphapi.orchestrator")


class ExtractionOrchestrator:
    def __init__(
        self,
        extractor: PlaywrightExtractionService | None = None,
        healer: LangGraphHealingEngine | None = None,
    ):
        self.extractor = extractor or PlaywrightExtractionService()
        self.healer = healer or LangGraphHealingEngine(self.extractor)

    async def execute_extraction(self, endpoint_id: str) -> ExtractionResponse:
        """
        Executes extraction for the given endpoint_id.
        Shared by REST GET /api/v1/extract/{id} and MCP tool extract_endpoint.
        """
        start_time = time.time()

        endpoint = await get_endpoint(endpoint_id)
        if not endpoint:
            raise KeyError(f"Endpoint '{endpoint_id}' is not registered.")

        target_url = endpoint["target_url"]
        selectors = endpoint.get("initial_selectors") or {}
        schema_def = endpoint["schema_definition"]

        await telemetry_hub.emit_event(
            event_type="EXTRACTION_STARTED",
            endpoint_id=endpoint_id,
            message=f"Starting extraction for '{endpoint_id}' ({target_url})",
            details={"selectors": selectors},
        )

        # -------------------------------------------------------------
        # STEP 1: FAST PATH (Cached selectors, zero LLM tokens)
        # -------------------------------------------------------------
        if selectors:
            logger.info(f"Attempting Fast Path for '{endpoint_id}' with selectors: {selectors}")
            result = await self.extractor.extract_data(
                target_url=target_url,
                selectors=selectors,
                schema_definition=schema_def,
            )

            if result.success and result.is_schema_valid:
                latency_ms = int((time.time() - start_time) * 1000)
                await record_telemetry(
                    endpoint_id=endpoint_id,
                    execution_path="FAST_PATH",
                    latency_ms=latency_ms,
                    http_status=200,
                )
                await telemetry_hub.emit_event(
                    event_type="FAST_PATH_OK",
                    endpoint_id=endpoint_id,
                    message=f"Fast path extraction completed in {latency_ms}ms",
                    latency_ms=latency_ms,
                    details={"data_sample_count": len(result.data) if isinstance(result.data, list) else 1},
                )
                return ExtractionResponse(
                    endpoint_id=endpoint_id,
                    data=result.data,
                    healed_this_request=False,
                    execution_path="FAST_PATH",
                    latency_ms=latency_ms,
                )

            failure_reason = "; ".join(result.validation_errors) or result.error_message or "Selector extraction failed or returned invalid data"
            logger.warning(f"Fast path failed for '{endpoint_id}': {failure_reason}. Escalating to LangGraph Self-Healing.")
        else:
            failure_reason = "No selectors configured; initial discovery required"

        # -------------------------------------------------------------
        # STEP 2: AUTONOMOUS LANGGRAPH AGENTIC HEALING FALLBACK
        # -------------------------------------------------------------
        try:
            healed_result, new_selectors, reasoning = await self.healer.execute_healing(
                endpoint_id=endpoint_id,
                initial_failure_reason=failure_reason,
                failing_selectors=selectors,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            await record_telemetry(
                endpoint_id=endpoint_id,
                execution_path="SELF_HEALED",
                latency_ms=latency_ms,
                http_status=200,
            )
            return ExtractionResponse(
                endpoint_id=endpoint_id,
                data=healed_result.data,
                healed_this_request=True,
                execution_path="SELF_HEALED",
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            await record_telemetry(
                endpoint_id=endpoint_id,
                execution_path="SELF_HEALED",
                latency_ms=latency_ms,
                http_status=502,
            )
            logger.exception(f"LangGraph extraction failed for '{endpoint_id}': {e}")
            raise


orchestrator_instance = ExtractionOrchestrator()

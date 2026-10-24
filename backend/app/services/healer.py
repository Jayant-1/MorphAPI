"""
MorphAPI Self-Healing Engine
Orchestrates autonomous visual and DOM-grounded repair using Playwright,
DOM Pruning, NVIDIA NIM (or offline fake adapter), and strict schema validation.
Persists patches ONLY after live verification succeeds.
"""

import asyncio
import logging
import os
import time
from typing import Any, Optional

from backend.app.adapters.nvidia_nim import NvidiaNimAdapter, CandidateSelectorsResponse, NIMInferenceError
from backend.app.database import (
    get_endpoint,
    update_endpoint_selectors,
    update_endpoint_status,
    record_healing_log,
)
from backend.app.models.contracts import ExtractionResult
from backend.app.services.dom_pruner import prune_html_to_ast_skeleton
from backend.app.services.extraction import PlaywrightExtractionService
from backend.app.services.telemetry import telemetry_hub

logger = logging.getLogger("morphapi.healer")

# Per-endpoint asynchronous lock map to prevent redundant concurrent healing
_endpoint_locks: dict[str, asyncio.Lock] = {}
_global_lock = asyncio.Lock()


async def get_endpoint_lock(endpoint_id: str) -> asyncio.Lock:
    async with _global_lock:
        if endpoint_id not in _endpoint_locks:
            _endpoint_locks[endpoint_id] = asyncio.Lock()
        return _endpoint_locks[endpoint_id]


class SelfHealingEngine:
    def __init__(self, extraction_service: Optional[PlaywrightExtractionService] = None):
        self.extractor = extraction_service or PlaywrightExtractionService()
        self.nim_adapter = NvidiaNimAdapter()
        self.fake_adapter = os.getenv("FAKE_ADAPTER", "false").lower() in ("true", "1")

    async def heal_and_extract(
        self,
        endpoint_id: str,
        initial_failure_reason: str,
        failing_selectors: dict[str, str],
    ) -> tuple[ExtractionResult, dict[str, str], str]:
        """
        Executes bounded self-healing workflow.
        Returns: (verified_extraction_result, verified_new_selectors, ai_reasoning)
        Raises: RuntimeError if healing cannot produce a verified extraction.
        """
        lock = await get_endpoint_lock(endpoint_id)

        async with lock:
            # Re-read endpoint after acquiring lock (double-checked locking)
            endpoint = await get_endpoint(endpoint_id)
            if not endpoint:
                raise ValueError(f"Endpoint '{endpoint_id}' not found")

            current_selectors = endpoint.get("initial_selectors") or {}
            current_version = endpoint.get("version", 1)
            target_url = endpoint["target_url"]
            schema_def = endpoint["schema_definition"]

            # If another coroutine already healed it while we waited for lock
            if current_selectors != failing_selectors and current_selectors:
                logger.info(f"Endpoint '{endpoint_id}' was already healed by another worker. Retrying with new selectors.")
                retry_result = await self.extractor.extract_data(
                    target_url=target_url,
                    selectors=current_selectors,
                    schema_definition=schema_def,
                )
                if retry_result.success and retry_result.is_schema_valid:
                    return retry_result, current_selectors, "Healed concurrently by parallel request"

            start_heal_time = time.time()

            await telemetry_hub.emit_event(
                event_type="HEALING_TRIGGERED",
                endpoint_id=endpoint_id,
                message=f"Self-healing triggered: {initial_failure_reason}",
                details={
                    "failure_reason": initial_failure_reason,
                    "failing_selectors": failing_selectors,
                    "version": current_version,
                },
            )

            # Step 1: Capture screenshot and DOM
            logger.info(f"Capturing visual and DOM context for '{endpoint_id}' at {target_url}")
            snapshot = await self.extractor.capture_context(target_url=target_url)
            screenshot_b64 = snapshot.get("screenshot_b64")
            raw_html = snapshot.get("html", "")
            page_title = snapshot.get("title", "")

            # Step 2: Prune DOM to reduce tokens by >=80%
            pruned_dom = prune_html_to_ast_skeleton(raw_html)

            await telemetry_hub.emit_event(
                event_type="HEALING_CONTEXT_CAPTURED",
                endpoint_id=endpoint_id,
                message="Visual viewport and pruned DOM context captured",
                details={
                    "page_title": page_title,
                    "has_screenshot": bool(screenshot_b64),
                    "dom_bytes": len(raw_html),
                    "pruned_bytes": len(pruned_dom),
                },
            )

            # Step 3: Consult VLM (NVIDIA NIM or offline fallback)
            candidate: CandidateSelectorsResponse
            if self.fake_adapter or not os.getenv("NVIDIA_NIM_API_KEY"):
                logger.info("Using deterministic offline selector discovery engine")
                candidate = self._discover_candidate_fallback(
                    raw_html=raw_html,
                    schema_def=schema_def,
                    previous_selectors=failing_selectors,
                )
            else:
                try:
                    candidate = await self.nim_adapter.propose_selectors(
                        target_url=target_url,
                        page_title=page_title,
                        schema_definition=schema_def,
                        pruned_dom=pruned_dom,
                        screenshot_b64=screenshot_b64,
                        previous_selectors=failing_selectors,
                        error_context=initial_failure_reason,
                    )
                except NIMInferenceError as nim_err:
                    logger.warning(f"NIM inference error: {nim_err}. Attempting fallback heuristics.")
                    candidate = self._discover_candidate_fallback(
                        raw_html=raw_html,
                        schema_def=schema_def,
                        previous_selectors=failing_selectors,
                    )

            await telemetry_hub.emit_event(
                event_type="HEALING_PATCH_PROPOSED",
                endpoint_id=endpoint_id,
                message="Candidate selector patch proposed",
                details={
                    "proposed_selectors": candidate.new_selectors,
                    "ai_reasoning": candidate.ai_reasoning,
                    "confidence_score": candidate.confidence_score,
                },
            )

            # Step 4: Verification gate — NEVER persist before verifying against live DOM!
            logger.info(f"Verifying candidate patch for '{endpoint_id}' with selectors: {candidate.new_selectors}")
            verification_result = await self.extractor.extract_data(
                target_url=target_url,
                selectors=candidate.new_selectors,
                schema_definition=schema_def,
            )

            heal_latency_ms = int((time.time() - start_heal_time) * 1000)

            if verification_result.success and verification_result.is_schema_valid:
                # PERSIST ONLY ON SUCCESS
                new_version = current_version + 1
                await update_endpoint_selectors(
                    endpoint_id=endpoint_id,
                    new_selectors=candidate.new_selectors,
                    new_version=new_version,
                    status="HEALTHY",
                )
                await record_healing_log(
                    endpoint_id=endpoint_id,
                    failure_reason=initial_failure_reason,
                    old_selectors=failing_selectors,
                    new_selectors=candidate.new_selectors,
                    ai_reasoning=candidate.ai_reasoning,
                    screenshot_b64=screenshot_b64,
                    heal_latency_ms=heal_latency_ms,
                    from_version=current_version,
                    to_version=new_version,
                )
                await telemetry_hub.emit_event(
                    event_type="HEAL_COMPLETE",
                    endpoint_id=endpoint_id,
                    message="Selector patch verified and persisted successfully",
                    latency_ms=heal_latency_ms,
                    details={
                        "old_selectors": failing_selectors,
                        "new_selectors": candidate.new_selectors,
                        "from_version": current_version,
                        "to_version": new_version,
                        "ai_reasoning": candidate.ai_reasoning,
                    },
                )
                await telemetry_hub.emit_event(
                    event_type="ENDPOINT_STATUS_CHANGED",
                    endpoint_id=endpoint_id,
                    message=f"Endpoint '{endpoint_id}' status updated to HEALTHY (v{new_version})",
                    details={"status": "HEALTHY", "version": new_version},
                )
                return verification_result, candidate.new_selectors, candidate.ai_reasoning

            # If candidate failed, mark DEGRADED
            logger.error(f"Candidate patch failed validation for '{endpoint_id}': {verification_result.validation_errors}")
            await update_endpoint_status(endpoint_id=endpoint_id, status="DEGRADED")
            await telemetry_hub.emit_event(
                event_type="HEALING_FAILED",
                endpoint_id=endpoint_id,
                message=f"Healing candidate failed validation: {'; '.join(verification_result.validation_errors)}",
                latency_ms=heal_latency_ms,
                details={"errors": verification_result.validation_errors},
            )
            await telemetry_hub.emit_event(
                event_type="ENDPOINT_STATUS_CHANGED",
                endpoint_id=endpoint_id,
                message=f"Endpoint '{endpoint_id}' marked as DEGRADED",
                details={"status": "DEGRADED"},
            )
            raise RuntimeError(
                f"Self-healing failed to verify patch: {'; '.join(verification_result.validation_errors or [verification_result.error_message or 'Unknown extraction error'])}"
            )

    def _discover_candidate_fallback(
        self,
        raw_html: str,
        schema_def: dict[str, str],
        previous_selectors: dict[str, str],
    ) -> CandidateSelectorsResponse:
        """
        Deterministic structural discovery engine used in tests and mock-chaos demo.
        Handles transition between mock-gov legacy table and modern card grid.
        """
        html_lower = raw_html.lower()
        new_sel: dict[str, str] = {}

        # Heuristic 1: Mock-Gov modern card structure
        if "modern-agri-card" in html_lower or "data-card-title" in html_lower or "card-grid" in html_lower:
            for field in schema_def.keys():
                fl = field.lower()
                if "crop" in fl or "name" in fl or "item" in fl:
                    new_sel[field] = "[data-card-title], .card-crop-name, .mandi-crop-v2"
                elif "price" in fl or "rate" in fl or "val" in fl:
                    new_sel[field] = ".new-price-badge, .card-price, .mandi-rate-v2"
                elif "market" in fl or "location" in fl:
                    new_sel[field] = ".card-market, .mandi-location"
                else:
                    new_sel[field] = f"[data-field='{field}'], .{field}"
            return CandidateSelectorsResponse(
                new_selectors=new_sel,
                ai_reasoning="Detected UI mutation from tabular rows to CSS Grid cards with data attributes",
                confidence_score=0.98,
                vision_enabled=False,
            )

        # Heuristic 2: Mock-Gov legacy table
        if "mandi-crop" in html_lower or "<table" in html_lower:
            for field in schema_def.keys():
                fl = field.lower()
                if "crop" in fl:
                    new_sel[field] = ".mandi-crop, td.crop"
                elif "price" in fl:
                    new_sel[field] = ".rate-val, td.rate"
                else:
                    new_sel[field] = f".{field}"
            return CandidateSelectorsResponse(
                new_selectors=new_sel,
                ai_reasoning="Detected standard tabular layout matching schema keywords",
                confidence_score=0.95,
                vision_enabled=False,
            )

        # Heuristic 3: Generic attribute matching
        for field in schema_def.keys():
            new_sel[field] = f"[data-field='{field}'], [name='{field}'], .{field}, #{field}"

        return CandidateSelectorsResponse(
            new_selectors=new_sel,
            ai_reasoning="Matched schema field names to DOM classes and data attributes",
            confidence_score=0.75,
            vision_enabled=False,
        )

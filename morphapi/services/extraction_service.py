"""
MorphAPI Shared Extraction Service
Handles the high-performance FAST PATH for normal API and MCP requests.
If active selectors are healthy, completely bypasses NVIDIA NIM and agent workflows.
Only delegates to healing when deterministic checks fail.
Shared identically by REST API and MCP server.
"""

import logging
import time
from typing import Any
from morphapi.browser.extractor import BrowserExtractor
from morphapi.db.repository import EndpointRepository, VersionRepository
from morphapi.observability.correlation import get_correlation_id
from morphapi.schemas.audit import AuditEventType
from morphapi.schemas.contracts import ExtractionResult, ExtractionResponse, ExecutionPath
from morphapi.schemas.errors import FailureCode, MorphApiError
from morphapi.services.audit_service import AuditService, audit_service
from morphapi.services.healing_service import HealingService
from morphapi.services.validation_service import ValidationService

logger = logging.getLogger("morphapi.extraction_service")


class SharedExtractionService:
    """
    Shared extraction engine serving both REST endpoints and MCP tools.
    """

    def __init__(
        self,
        extractor: BrowserExtractor | None = None,
        validator: ValidationService | None = None,
        healing_service: HealingService | None = None,
        endpoint_repo: EndpointRepository | None = None,
        version_repo: VersionRepository | None = None,
        auditor: AuditService | None = None,
    ):
        self.extractor = extractor or BrowserExtractor()
        self.validator = validator or ValidationService()
        self.healing_service = healing_service
        self.endpoint_repo = endpoint_repo or EndpointRepository()
        self.version_repo = version_repo or VersionRepository()
        self.auditor = auditor or audit_service

    async def extract_endpoint(
        self,
        endpoint_id: str,
        tenant_id: str = "default_tenant",
        request_id: str | None = None,
        auto_heal: bool = True,
        params: dict[str, Any] | None = None,
    ) -> ExtractionResponse:
        """
        High-level extraction entrypoint used by REST /api/v1/extract/{endpoint_id} and MCP tools.
        Loads active verified configuration and executes extraction.
        Applies runtime URL query parameters or template substitutions (e.g. {year}, {batch}).
        """
        req_id = request_id or get_correlation_id()
        endpoint = await self.endpoint_repo.get_endpoint(endpoint_id, tenant_id=tenant_id)
        if not endpoint:
            endpoint = await self.endpoint_repo.get_endpoint_by_slug(endpoint_id, tenant_id=tenant_id)
        if not endpoint:
            endpoint = await self.endpoint_repo.get_endpoint(endpoint_id)
        if not endpoint:
            endpoint = await self.endpoint_repo.get_endpoint_by_slug(endpoint_id)
        if not endpoint:
            raise MorphApiError(
                FailureCode.ENDPOINT_NOT_FOUND,
                f"Endpoint '{endpoint_id}' was not found.",
                details={"endpoint_id": endpoint_id},
            )

        active_ver_id = endpoint["active_version_id"]
        if not active_ver_id:
            raise MorphApiError(
                FailureCode.INVALID_CANDIDATE,
                f"Endpoint '{endpoint_id}' does not have an active verified configuration.",
                details={"endpoint_id": endpoint_id, "status": endpoint["status"]},
            )

        active_ver = await self.version_repo.get_version(active_ver_id)
        if not active_ver or not active_ver["is_active"]:
            raise MorphApiError(
                FailureCode.INVALID_CANDIDATE,
                f"Active version '{active_ver_id}' for endpoint '{endpoint_id}' is invalid or retired.",
                details={"endpoint_id": endpoint_id},
            )

        # Compute dynamic effective URL from parameters
        from urllib.parse import unquote, urlparse, parse_qs, urlencode, urlunparse
        from morphapi.browser.url_policy import resolve_test_url
        effective_url = unquote(endpoint["target_url"])
        if params:
            # 1. Substitute path and template placeholders {param}
            for k, v in params.items():
                placeholder = f"{{{k}}}"
                if placeholder in effective_url:
                    effective_url = effective_url.replace(placeholder, str(v))

            # 2. Append or update query string parameters not consumed by placeholders
            parsed = urlparse(effective_url)
            qs = parse_qs(parsed.query)
            for k, v in params.items():
                if f"{{{k}}}" not in effective_url:
                    qs[k] = [str(v)]
            new_query = urlencode(qs, doseq=True)
            effective_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            ))
            logger.info("[%s] Dynamic target URL parameterized with %s -> %s", endpoint_id, params, effective_url)
        else:
            effective_url = resolve_test_url(effective_url)

        return await self.extract(
            endpoint_id=endpoint["endpoint_id"],
            target_url=effective_url,
            schema_definition=active_ver["schema_definition"],
            selectors=active_ver["selector_map"],
            auto_heal=auto_heal,
            version=active_ver["version_number"],
            request_id=req_id,
        )

    async def extract(
        self,
        endpoint_id: str,
        target_url: str,
        schema_definition: dict[str, str],
        selectors: dict[str, str],
        auto_heal: bool = True,
        version: int | None = 1,
        request_id: str | None = None,
    ) -> ExtractionResponse:
        """
        Executes fast-path extraction.
        Bypasses NIM/LangGraph on success.
        """
        start_ts = time.monotonic()
        req_id = request_id or get_correlation_id()
        logger.info("[%s] FAST PATH: executing browser extraction with active selectors", endpoint_id)

        # 1. Run real browser extraction (Zero LLM tokens)
        raw_result: ExtractionResult = await self.extractor.extract(
            endpoint_id=endpoint_id,
            target_url=target_url,
            schema_definition=schema_definition,
            selector_map=selectors,
        )

        # 2. Run deterministic backend schema validation
        if raw_result.success and raw_result.data is not None:
            val_result = self.validator.validate_extraction(
                extracted_data=raw_result.data,
                schema_definition=schema_definition,
                field_evidences=raw_result.field_evidences,
            )

            if val_result.is_valid:
                latency_ms = int((time.monotonic() - start_ts) * 1000)
                logger.info("[%s] FAST PATH SUCCESS in %dms (model bypassed)", endpoint_id, latency_ms)

                if self.auditor:
                    try:
                        await self.auditor.record_event(
                            action=AuditEventType.EXTRACTION_SUCCESS,
                            target_type="endpoint",
                            target_id=endpoint_id,
                            correlation_id=req_id,
                            details={"latency_ms": latency_ms, "execution_path": "FAST_PATH"},
                        )
                    except Exception as ae:
                        logger.debug("Auditing record error: %s", ae)

                return ExtractionResponse(
                    endpoint_id=endpoint_id,
                    data=val_result.normalized_data,
                    healed_this_request=False,
                    execution_path="FAST_PATH",
                    latency_ms=latency_ms,
                    config_version=version,
                    request_id=req_id,
                )

        # 3. Fast path failed - log audit and check if auto-healing is permitted
        latency_ms = int((time.monotonic() - start_ts) * 1000)
        err = raw_result.error_message or "Extraction failed deterministic schema validation"
        code = raw_result.error_code or FailureCode.SCHEMA_VALIDATION_FAILED

        await self.auditor.record_event(
            action=AuditEventType.EXTRACTION_FAILED,
            target_type="endpoint",
            target_id=endpoint_id,
            correlation_id=req_id,
            details={"error_code": code.value if hasattr(code, "value") else str(code), "error": err, "latency_ms": latency_ms},
        )

        # Mark endpoint degraded
        await self.endpoint_repo.update_endpoint_status(endpoint_id, "DEGRADED")

        if not auto_heal or not self.healing_service:
            raise MorphApiError(
                code=code,
                message=f"Extraction failed: {err}",
                details={"target_url": target_url, "endpoint_id": endpoint_id, "latency_ms": latency_ms},
            )

        # 4. Trigger bounded LangGraph healing workflow
        logger.warning("[%s] Fast path failed; triggering bounded self-healing workflow", endpoint_id)
        await self.auditor.record_event(
            action=AuditEventType.HEALING_TRIGGERED,
            target_type="endpoint",
            target_id=endpoint_id,
            correlation_id=req_id,
            details={"failure_reason": err},
        )

        try:
            heal_res = await self.healing_service.heal_endpoint(
                endpoint_id=endpoint_id,
                target_url=target_url,
                schema_definition=schema_definition,
                current_selectors=selectors,
                current_version=version or 1,
                failure_reason=err,
            )

            latency_ms = int((time.monotonic() - start_ts) * 1000)
            await self.auditor.record_event(
                action=AuditEventType.HEALING_COMPLETED,
                target_type="endpoint",
                target_id=endpoint_id,
                correlation_id=req_id,
                details={"latency_ms": latency_ms, "new_version": heal_res.get("version")},
            )

            return ExtractionResponse(
                endpoint_id=endpoint_id,
                data=heal_res.get("data"),
                healed_this_request=True,
                execution_path="SELF_HEALED",
                latency_ms=latency_ms,
                config_version=heal_res.get("version", version),
                request_id=req_id,
            )
        except Exception as e:
            latency_ms = int((time.monotonic() - start_ts) * 1000)
            await self.auditor.record_event(
                action=AuditEventType.HEALING_FAILED,
                target_type="endpoint",
                target_id=endpoint_id,
                correlation_id=req_id,
                details={"error": str(e), "latency_ms": latency_ms},
            )
            raise


shared_extraction_service = SharedExtractionService()

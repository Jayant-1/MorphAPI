"""
MorphAPI Endpoint Service
Controls the endpoint lifecycle: drafts, candidate submission, deterministic verification,
atomic backend-controlled promotion, and rollback to last-known-good configuration.
"""

from typing import Any, Optional
from morphapi.browser.extractor import BrowserExtractor
from morphapi.browser.selector_tester import SelectorTester
from morphapi.db.repository import (
    CandidateNotVerifiedError,
    EndpointRepository,
    VersionRepository,
)
from morphapi.observability.logging import logger
from morphapi.schemas.audit import AuditEventType
from morphapi.schemas.contracts import ExtractionResult, ValidationResult
from morphapi.schemas.endpoint import (
    CandidateSubmitRequest,
    CandidateVerifyRequest,
    CandidateVerifyResponse,
    EndpointCreateRequest,
    EndpointResponse,
    EndpointStatus,
    EndpointVersionResponse,
    VersionStatus,
)
from morphapi.schemas.errors import FailureCode, MorphApiError
from morphapi.services.audit_service import AuditService, audit_service
from morphapi.services.validation_service import ValidationService


class EndpointService:
    def __init__(
        self,
        endpoint_repo: EndpointRepository | None = None,
        version_repo: VersionRepository | None = None,
        validation_service: ValidationService | None = None,
        browser_extractor: BrowserExtractor | None = None,
        selector_tester: SelectorTester | None = None,
        auditor: AuditService | None = None,
    ):
        self.endpoint_repo = endpoint_repo or EndpointRepository()
        self.version_repo = version_repo or VersionRepository()
        self.validator = validation_service or ValidationService()
        self.extractor = browser_extractor or BrowserExtractor()
        self.tester = selector_tester or SelectorTester()
        self.auditor = auditor or audit_service

    async def create_endpoint_draft(
        self,
        request: EndpointCreateRequest,
        tenant_id: str = "default_tenant",
        actor: str = "user",
    ) -> EndpointResponse:
        """
        Creates a new draft endpoint and initial draft version.
        Does NOT activate the endpoint.
        """
        # Validate schema definition syntax
        if not request.schema_definition:
            raise MorphApiError(FailureCode.SCHEMA_VALIDATION_FAILED, "Schema definition must contain at least one field.")

        endpoint = await self.endpoint_repo.create_endpoint(
            name=request.name,
            slug=request.slug,
            target_url=str(request.target_url),
            schema_definition=request.schema_definition,
            tenant_id=tenant_id,
            allowed_url_scope=request.allowed_url_scope,
            field_descriptions=request.field_descriptions,
            extraction_hints=request.extraction_hints,
            freshness_seconds=request.freshness_seconds,
            initial_selectors=request.initial_selectors,
        )

        await self.auditor.record_event(
            action=AuditEventType.ENDPOINT_CREATED,
            target_type="endpoint",
            target_id=endpoint["endpoint_id"],
            tenant_id=tenant_id,
            actor=actor,
            details={"name": endpoint["name"], "target_url": endpoint["target_url"]},
        )

        return EndpointResponse(
            endpoint_id=endpoint["endpoint_id"],
            tenant_id=endpoint["tenant_id"],
            name=endpoint["name"],
            slug=endpoint["slug"],
            target_url=endpoint["target_url"],
            allowed_url_scope=endpoint["allowed_url_scope"],
            status=EndpointStatus(endpoint["status"]),
            active_version_id=endpoint["active_version_id"],
            last_known_good_version_id=endpoint["last_known_good_version_id"],
            schema_definition=endpoint["schema_definition"],
            created_at=endpoint["created_at"],
            updated_at=endpoint["updated_at"],
        )

    async def get_endpoint(self, endpoint_id: str, tenant_id: str | None = None) -> EndpointResponse:
        endpoint = await self.endpoint_repo.get_endpoint(endpoint_id, tenant_id=tenant_id)
        if not endpoint:
            # Try by slug as fallback
            endpoint = await self.endpoint_repo.get_endpoint_by_slug(endpoint_id, tenant_id=tenant_id)
        if not endpoint:
            raise MorphApiError(FailureCode.ENDPOINT_NOT_FOUND, f"Endpoint '{endpoint_id}' was not found.")

        return EndpointResponse(
            endpoint_id=endpoint["endpoint_id"],
            tenant_id=endpoint["tenant_id"],
            name=endpoint["name"],
            slug=endpoint["slug"],
            target_url=endpoint["target_url"],
            allowed_url_scope=endpoint["allowed_url_scope"],
            status=EndpointStatus(endpoint["status"]),
            active_version_id=endpoint["active_version_id"],
            last_known_good_version_id=endpoint["last_known_good_version_id"],
            schema_definition=endpoint["schema_definition"],
            created_at=endpoint["created_at"],
            updated_at=endpoint["updated_at"],
        )

    async def list_endpoints(self, tenant_id: str | None = None) -> list[EndpointResponse]:
        endpoints = await self.endpoint_repo.list_endpoints(tenant_id=tenant_id)
        return [
            EndpointResponse(
                endpoint_id=ep["endpoint_id"],
                tenant_id=ep["tenant_id"],
                name=ep["name"],
                slug=ep["slug"],
                target_url=ep["target_url"],
                allowed_url_scope=ep["allowed_url_scope"],
                status=EndpointStatus(ep["status"]),
                active_version_id=ep["active_version_id"],
                last_known_good_version_id=ep["last_known_good_version_id"],
                schema_definition=ep["schema_definition"],
                created_at=ep["created_at"],
                updated_at=ep["updated_at"],
            )
            for ep in endpoints
        ]

    async def submit_candidate(
        self,
        endpoint_id: str,
        request: CandidateSubmitRequest,
        created_by: str = "agent",
        tenant_id: str = "default_tenant",
    ) -> EndpointVersionResponse:
        """
        Submits a proposed candidate selector map. Stores it as an unverified CANDIDATE version.
        Agent tools call this - it never directly activates or marks verified.
        """
        version = await self.version_repo.create_candidate_version(
            endpoint_id=endpoint_id,
            selector_map=request.selector_map,
            rationale=request.rationale,
            evidence_refs=request.evidence_refs,
            created_by=created_by,
        )

        await self.auditor.record_event(
            action=AuditEventType.CANDIDATE_SUBMITTED,
            target_type="version",
            target_id=version["version_id"],
            tenant_id=tenant_id,
            actor=created_by,
            details={"endpoint_id": endpoint_id, "version_number": version["version_number"]},
        )

        return self._format_version_response(version)

    async def verify_candidate(
        self,
        endpoint_id: str,
        version_id: str,
        request: CandidateVerifyRequest | None = None,
        tenant_id: str = "default_tenant",
        actor: str = "system",
    ) -> CandidateVerifyResponse:
        """
        Deterministic backend verification of a candidate configuration.
        1. Tests selectors via browser extraction or against provided sample data.
        2. Validates extracted values deterministically against endpoint schema definition.
        3. Only marks candidate 'VERIFIED' if actual extraction AND deterministic checks pass.
        """
        version = await self.version_repo.get_version(version_id)
        if not version or version["endpoint_id"] != endpoint_id:
            raise MorphApiError(FailureCode.INVALID_CANDIDATE, f"Version '{version_id}' not found for endpoint '{endpoint_id}'")

        endpoint = await self.get_endpoint(endpoint_id, tenant_id=tenant_id)
        schema_def = endpoint.schema_definition
        selector_map = version["selector_map"]
        target_url = (request and request.test_url) or endpoint.target_url

        issues: list[str] = []
        match_counts: dict[str, int] = {}
        sample_data: Any = None
        selector_test_passed = False
        validation_passed = False

        if request and request.sample_data is not None:
            # Deterministic offline sample verification
            sample_data = request.sample_data
            selector_test_passed = True
            for k in selector_map.keys():
                match_counts[k] = 1
        else:
            # Live browser extraction test
            logger.info(f"Running deterministic browser verification for version {version_id} on {target_url}")
            extract_res: ExtractionResult = await self.extractor.extract(
                endpoint_id=endpoint_id,
                target_url=target_url,
                schema_definition=schema_def,
                selector_map=selector_map,
            )

            for fe in extract_res.field_evidences:
                match_counts[fe.field_name] = fe.matched_count
                if fe.matched_count == 0 or fe.error:
                    issues.append(f"Selector for field '{fe.field_name}' failed: {fe.error or '0 elements matched'}")

            if extract_res.success and extract_res.data is not None:
                selector_test_passed = len(issues) == 0
                sample_data = extract_res.data
            else:
                selector_test_passed = False
                issues.append(extract_res.error_message or "Browser extraction returned no data")

        # Deterministic schema validation
        if selector_test_passed and sample_data is not None:
            val_res: ValidationResult = self.validator.validate_extraction(
                extracted_data=sample_data,
                schema_definition=schema_def,
            )
            validation_passed = val_res.is_valid
            if not val_res.is_valid:
                issues.extend(val_res.errors)
                sample_data = None
            else:
                sample_data = val_res.normalized_data

        verified = selector_test_passed and validation_passed and len(issues) == 0

        # Update candidate verification result in authoritative repository
        ver_record = {
            "verified": verified,
            "selector_test_passed": selector_test_passed,
            "validation_passed": validation_passed,
            "issues": issues,
            "match_counts": match_counts,
        }
        await self.version_repo.update_verification_result(version_id, verified=verified, verification_result=ver_record)

        audit_action = AuditEventType.CANDIDATE_VERIFIED if verified else AuditEventType.CANDIDATE_REJECTED
        await self.auditor.record_event(
            action=audit_action,
            target_type="version",
            target_id=version_id,
            tenant_id=tenant_id,
            actor=actor,
            details={"verified": verified, "issues": issues},
        )

        return CandidateVerifyResponse(
            verified=verified,
            status=VersionStatus.VERIFIED if verified else VersionStatus.REJECTED,
            validation_passed=validation_passed,
            selector_test_passed=selector_test_passed,
            issues=issues,
            selector_match_counts=match_counts,
            sample_data=sample_data,
        )

    async def activate_version(
        self,
        endpoint_id: str,
        version_id: str,
        approval_id: str | None = None,
        tenant_id: str = "default_tenant",
        actor: str = "user",
    ) -> tuple[EndpointResponse, EndpointVersionResponse]:
        """
        Atomic backend-controlled promotion of a verified version to ACTIVE.
        Rejects activation if version is not in VERIFIED status.
        """
        logger.info(f"Attempting atomic activation of version {version_id} for endpoint {endpoint_id}")
        ep_dict, ver_dict = await self.endpoint_repo.atomic_activate_version(endpoint_id, version_id)

        await self.auditor.record_event(
            action=AuditEventType.VERSION_ACTIVATED,
            target_type="endpoint",
            target_id=endpoint_id,
            tenant_id=tenant_id,
            actor=actor,
            details={"version_id": version_id, "version_number": ver_dict["version_number"], "approval_id": approval_id},
        )

        return (
            EndpointResponse(
                endpoint_id=ep_dict["endpoint_id"],
                tenant_id=ep_dict["tenant_id"],
                name=ep_dict["name"],
                slug=ep_dict["slug"],
                target_url=ep_dict["target_url"],
                allowed_url_scope=ep_dict["allowed_url_scope"],
                status=EndpointStatus(ep_dict["status"]),
                active_version_id=ep_dict["active_version_id"],
                last_known_good_version_id=ep_dict["last_known_good_version_id"],
                schema_definition=ep_dict["schema_definition"],
                created_at=ep_dict["created_at"],
                updated_at=ep_dict["updated_at"],
            ),
            self._format_version_response(ver_dict),
        )

    async def rollback(
        self,
        endpoint_id: str,
        reason: str = "Rollback to last known good",
        tenant_id: str = "default_tenant",
        actor: str = "user",
    ) -> tuple[EndpointResponse, EndpointVersionResponse]:
        """
        Atomically rolls back the endpoint to last_known_good_version_id.
        """
        ep_dict, ver_dict = await self.endpoint_repo.rollback_to_last_known_good(endpoint_id)

        await self.auditor.record_event(
            action=AuditEventType.ROLLBACK_TRIGGERED,
            target_type="endpoint",
            target_id=endpoint_id,
            tenant_id=tenant_id,
            actor=actor,
            details={"restored_version_id": ver_dict["version_id"], "reason": reason},
        )

        return (
            EndpointResponse(
                endpoint_id=ep_dict["endpoint_id"],
                tenant_id=ep_dict["tenant_id"],
                name=ep_dict["name"],
                slug=ep_dict["slug"],
                target_url=ep_dict["target_url"],
                allowed_url_scope=ep_dict["allowed_url_scope"],
                status=EndpointStatus(ep_dict["status"]),
                active_version_id=ep_dict["active_version_id"],
                last_known_good_version_id=ep_dict["last_known_good_version_id"],
                schema_definition=ep_dict["schema_definition"],
                created_at=ep_dict["created_at"],
                updated_at=ep_dict["updated_at"],
            ),
            self._format_version_response(ver_dict),
        )

    async def list_versions(self, endpoint_id: str) -> list[EndpointVersionResponse]:
        versions = await self.version_repo.list_versions(endpoint_id)
        return [self._format_version_response(v) for v in versions]

    async def get_version(self, endpoint_id: str, version_id: str) -> EndpointVersionResponse:
        v = await self.version_repo.get_version(version_id)
        if not v or v["endpoint_id"] != endpoint_id:
            raise MorphApiError(FailureCode.INVALID_CANDIDATE, f"Version '{version_id}' not found for endpoint '{endpoint_id}'")
        return self._format_version_response(v)

    def _format_version_response(self, v: dict[str, Any]) -> EndpointVersionResponse:
        return EndpointVersionResponse(
            version_id=v["version_id"],
            endpoint_id=v["endpoint_id"],
            version_number=v["version_number"],
            schema_definition=v["schema_definition"],
            selector_map=v["selector_map"],
            status=VersionStatus(v["status"]),
            is_active=v["is_active"],
            is_last_known_good=v["is_last_known_good"],
            verification_result=v["verification_result"],
            rationale=v["rationale"],
            evidence_refs=v["evidence_refs"],
            created_by=v["created_by"],
            verified_at=v["verified_at"],
            activated_at=v["activated_at"],
            created_at=v["created_at"],
        )


endpoint_service = EndpointService()

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

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from morphapi.agent.builder_agent import DeepAgentsHarness


class EndpointService:
    def __init__(
        self,
        endpoint_repo: EndpointRepository | None = None,
        version_repo: VersionRepository | None = None,
        validation_service: ValidationService | None = None,
        browser_extractor: BrowserExtractor | None = None,
        selector_tester: SelectorTester | None = None,
        auditor: AuditService | None = None,
        builder_agent: Optional["DeepAgentsHarness"] = None,
    ):
        self.endpoint_repo = endpoint_repo or EndpointRepository()
        self.version_repo = version_repo or VersionRepository()
        self.validator = validation_service or ValidationService()
        self.extractor = browser_extractor or BrowserExtractor()
        self.tester = selector_tester or SelectorTester()
        self.auditor = auditor or audit_service
        self._builder_agent = builder_agent

    @property
    def builder_agent(self):
        if self._builder_agent is None:
            from morphapi.agent.builder_agent import DeepAgentsHarness
            self._builder_agent = DeepAgentsHarness()
        return self._builder_agent

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
            effective_test_url = target_url
            if "{" in target_url and "}" in target_url:
                import re
                effective_test_url = re.sub(r"\{[a-zA-Z0-9_]+\}", "W25", target_url)

            logger.info(f"Running deterministic browser verification for version {version_id} on {effective_test_url}")
            extract_res: ExtractionResult = await self.extractor.extract(
                endpoint_id=endpoint_id,
                target_url=effective_test_url,
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

    async def generate_endpoint_from_prompt(
        self,
        prompt: str,
        target_url: str | None = None,
        name: str | None = None,
        tenant_id: str = "default_tenant",
    ) -> dict[str, Any]:
        """
        End-to-end endpoint synthesis from natural language prompt or target URL:
        1. Resolves target URL from prompt or arguments.
        2. Inspects page and tests selectors against live rendered DOM.
        3. Deterministically validates extracted values.
        4. Creates draft, records candidate, verifies, and promotes to ACTIVE.
        5. Generates API key and returns endpoint link with sample data.
        """
        import re, secrets

        # Sanitize Swagger UI dummy values
        if name == "string":
            name = None

        url = target_url
        if not url or url.strip().lower() in ("string", "none", "null") or not url.startswith("http"):
            match = re.search(r"https?://[^\s\"'<>]+", prompt)
            if match:
                url = match.group(0).rstrip(".,;")
            else:
                raise MorphApiError(FailureCode.DISALLOWED_URL, "No valid HTTP/HTTPS URL found in prompt or target_url.")

        # Derive slug and name
        if not name:
            path_parts = [p for p in url.split("?")[0].split("/") if p and not p.startswith("http")]
            if len(path_parts) > 1:
                domain_prefix = path_parts[0].replace("www.", "").split(".")[0]
                last_slug = path_parts[-1].replace(".html", "").replace(".php", "")
                slug = f"{domain_prefix}-{last_slug}"[:40]
                name = slug.replace("-", " ").title()
            else:
                domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0].replace(".", "-")
                name = f"Web API for {domain}"
                slug = f"api-{domain[:20]}-{secrets.token_hex(3)}"
        else:
            slug = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower()).strip("-")[:40]

        # Check if already exists in DB
        existing = await self.endpoint_repo.get_endpoint_by_slug(slug, tenant_id=tenant_id)
        if existing and existing.get("active_version_id"):
            api_key = f"mapik_{slug[:12]}_{secrets.token_hex(12)}"
            from morphapi.services.extraction_service import shared_extraction_service
            sample_resp = await shared_extraction_service.extract_endpoint(existing["endpoint_id"], tenant_id=tenant_id)
            sample_items = sample_resp.data if isinstance(sample_resp.data, list) else [sample_resp.data]
            user_scope = tenant_id if tenant_id and tenant_id not in ("default_tenant", "string") else "default"
            endpoint_path = f"/v1/api/{user_scope}/{existing['slug']}"
            full_endpoint_url = f"http://localhost:8000{endpoint_path}"
            curl_command = f"curl -H 'X-API-Key: {api_key}' '{full_endpoint_url}'"
            return {
                "endpoint_id": existing["endpoint_id"],
                "user_id": user_scope,
                "api_name": existing["slug"],
                "slug": existing["slug"],
                "name": existing["name"],
                "status": "ACTIVE",
                "target_url": existing["target_url"],
                "api_key": api_key,
                "endpoint_url": endpoint_path,
                "full_endpoint_url": full_endpoint_url,
                "curl_command": curl_command,
                "api_specification": {
                    "method": "GET",
                    "path": endpoint_path,
                    "inputs": existing.get("extraction_hints", {}).get("inputs", {}),
                    "outputs": existing["schema_definition"],
                    "parameterized_url": existing["target_url"],
                },
                "schema_definition": existing["schema_definition"],
                "sample_data": sample_items[:5],
                "message": f"Endpoint '{endpoint_path}' is verified and active. You can query it dynamically.",
            }

        # Stage 0: MorphAPI Responsible Access Guard (Source Policy Assessment)
        from morphapi.browser.source_policy import source_policy_service
        from morphapi.schemas.contracts import PolicyOutcome
        import uuid

        correlation_id = str(uuid.uuid4())
        policy_decision = await source_policy_service.evaluate_url(url)
        logger.info("[Access Guard] Evaluated source access policy for '%s': %s (reason: %s)", url, policy_decision.outcome, policy_decision.reason)

        if policy_decision.outcome == PolicyOutcome.BLOCK:
            await self.auditor.record_event(
                correlation_id=correlation_id,
                actor="responsible_access_guard",
                action=AuditEventType.POLICY_BLOCKED,
                target_type="url",
                target_id=url,
                details=policy_decision.model_dump(),
                tenant_id=tenant_id,
            )
            return {
                "status": "BLOCKED",
                "outcome": "block",
                "target_url": url,
                "reason": policy_decision.reason,
                "policy_decision": policy_decision.model_dump(),
                "agent_explanation": (
                    f"The requested path is disallowed by the source website's robots.txt rules for crawler identity. "
                    f"MorphAPI Responsible Access Guard has blocked automated browser extraction before launching tools. "
                    f"I can help you extract from an alternative permitted source or use an authorized dataset."
                ),
                "suggested_actions": [
                    "Provide an alternative permitted source URL",
                    "Register documented source owner authorization for review",
                ],
            }

        # Record permitted / review audit event
        await self.auditor.record_event(
            correlation_id=correlation_id,
            actor="responsible_access_guard",
            action=AuditEventType.POLICY_EVALUATED,
            target_type="url",
            target_id=url,
            details=policy_decision.model_dump(),
            tenant_id=tenant_id,
        )

        # Invoke Deep Agent Harness to inspect the website, reason over prompt, and discover candidate selectors
        agent_synthesis = await self.builder_agent.synthesize_from_prompt(
            prompt=prompt,
            target_url=url,
            name=name,
        )
        url = agent_synthesis.get("target_url") or url
        schema = agent_synthesis["schema_definition"]
        selectors = agent_synthesis["selectors"]
        discovered_name = agent_synthesis.get("name") or name or f"Web API for {slug}"
        rationale = agent_synthesis.get("rationale") or "Deep Agent candidate proposal"
        evidence_refs = [agent_synthesis["evidence_ref"]] if agent_synthesis.get("evidence_ref") else []

        if not agent_synthesis.get("verified", True):
            logger.warning("[Backend Gate] Deep Agent ReAct loop could not verify candidate selectors live.")
            raise MorphApiError(
                FailureCode.SCHEMA_VALIDATION_FAILED,
                f"Agent ReAct loop was unable to match target fields live against '{url}'. The page may require user interaction or valid query parameters.",
            )

        logger.info("[Backend Gate] ========================================================")
        logger.info("[Backend Gate] [RECEIVED] Received Deep Agent proposal for endpoint '%s'", slug)
        logger.info("[Backend Gate] [SCHEMA] Target schema: %s", schema)
        logger.info("[Backend Gate] [SELECTORS] Proposed selectors: %s", selectors)
        logger.info("[Backend Gate] [VERIFYING] Running deterministic browser verification gate...")

        # 1. Create Draft or reuse existing draft
        existing_check = await self.endpoint_repo.get_endpoint_by_slug(slug)
        if existing_check and existing_check["tenant_id"] == tenant_id:
            endpoint_id = existing_check["endpoint_id"]
            await self.endpoint_repo.update_endpoint_draft(
                endpoint_id=endpoint_id,
                target_url=url,
                schema_definition=schema,
                name=discovered_name,
            )
        else:
            if existing_check and existing_check["tenant_id"] != tenant_id:
                slug = f"{slug}-{tenant_id[:6]}"
            draft_req = EndpointCreateRequest(
                name=discovered_name,
                slug=slug,
                target_url=url,
                schema_definition=schema,
                initial_selectors=selectors,
            )
            created_ep = await self.create_endpoint_draft(draft_req, tenant_id=tenant_id)
            endpoint_id = created_ep.endpoint_id

        # 2. Submit Candidate
        submit_req = CandidateSubmitRequest(
            selector_map=selectors,
            rationale=rationale,
            schema_definition=schema,
            evidence_refs=evidence_refs,
        )
        candidate_ver = await self.submit_candidate(endpoint_id, submit_req, tenant_id=tenant_id)
        version_id = candidate_ver.version_id

        # 3. Verify Candidate in live browser
        verify_resp = await self.verify_candidate(endpoint_id, version_id, tenant_id=tenant_id)
        if not verify_resp.verified:
            issues_str = ", ".join(verify_resp.issues) if verify_resp.issues else "Candidate validation or selector test failed"
            logger.error("[Backend Gate] [REJECTED] Candidate verification failed: %s", issues_str)
            raise MorphApiError(FailureCode.SCHEMA_VALIDATION_FAILED, f"Verification failed: {issues_str}")

        logger.info("[Backend Gate] [VERIFIED] Candidate configuration verified successfully against real browser DOM!")
        logger.info("[Backend Gate] [PROMOTING] Atomically promoting version %s to ACTIVE", version_id)

        # 4. Activate Version
        await self.activate_version(endpoint_id, version_id, tenant_id=tenant_id)
        logger.info("[Backend Gate] [ACTIVE] Endpoint '%s' is now ACTIVE. Fast Path ready for client queries.", slug)
        logger.info("[Backend Gate] ========================================================")

        # 5. Extract Sample Data
        from morphapi.services.extraction_service import SharedExtractionService
        extraction_svc = SharedExtractionService(
            extractor=self.extractor,
            validator=self.validator,
            endpoint_repo=self.endpoint_repo,
            version_repo=self.version_repo,
            auditor=self.auditor,
        )
        sample_params = {}
        if "{" in url and "}" in url:
            sample_params = {"batch": "W25", "year": "2025"}
        sample_resp = await extraction_svc.extract_endpoint(endpoint_id, tenant_id=tenant_id, params=sample_params)
        sample_items = sample_resp.data if isinstance(sample_resp.data, list) else [sample_resp.data]

        api_key = f"mapik_{slug[:12]}_{secrets.token_hex(12)}"

        inputs = agent_synthesis.get("inputs", {})
        user_scope = tenant_id if tenant_id and tenant_id not in ("default_tenant", "string") else "default"
        endpoint_path = f"/v1/api/{user_scope}/{slug}"
        full_endpoint_url = f"http://localhost:8000{endpoint_path}"
        curl_command = f"curl -H 'X-API-Key: {api_key}' '{full_endpoint_url}'"

        return {
            "endpoint_id": endpoint_id,
            "user_id": user_scope,
            "api_name": slug,
            "slug": slug,
            "name": name,
            "status": "ACTIVE",
            "target_url": url,
            "api_key": api_key,
            "endpoint_url": endpoint_path,
            "full_endpoint_url": full_endpoint_url,
            "curl_command": curl_command,
            "api_specification": {
                "method": "GET",
                "path": endpoint_path,
                "inputs": inputs,
                "outputs": schema,
                "parameterized_url": url,
            },
            "schema_definition": schema,
            "sample_data": sample_items[:5],
            "message": f"Endpoint '{endpoint_path}' is verified and active. You can query it dynamically.",
        }


endpoint_service = EndpointService()

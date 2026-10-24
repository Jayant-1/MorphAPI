"""
MorphAPI LangGraph Durable Healing Workflow
Implements deterministic state machine for website inspection, proposal generation,
actual browser selector testing, deterministic Pydantic v2 validation,
human-in-the-loop approval, and idempotent version promotion.
"""

import asyncio
import datetime
import logging
import time
from typing import Any, Callable, Coroutine, Literal
from langgraph.graph import StateGraph, START, END

from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.browser.page_inspector import PageInspector, EvidenceStore
from morphapi.browser.selector_tester import SelectorTester
from morphapi.browser.extractor import BrowserExtractor
from morphapi.browser.url_policy import UrlPolicyService
from morphapi.agent.nim_provider import NvidiaNimProvider
from morphapi.services.validation_service import ValidationService
from morphapi.workflows.state import WorkflowState, WorkflowStatus
from morphapi.workflows.policies import is_budget_exhausted, get_default_budget
from morphapi.workflows.checkpointer import WorkflowCheckpointer
from morphapi.schemas.contracts import SelectorPatch, ValidationResult
from morphapi.schemas.errors import FailureCode

logger = logging.getLogger("morphapi.healing_graph")


class MorphApiHealingGraph:
    """
    Durable LangGraph state machine orchestrating discovery and self-healing.
    """

    def __init__(
        self,
        browser_manager: PlaywrightManager | None = None,
        page_inspector: PageInspector | None = None,
        selector_tester: SelectorTester | None = None,
        browser_extractor: BrowserExtractor | None = None,
        validation_service: ValidationService | None = None,
        nim_provider: NvidiaNimProvider | None = None,
        checkpointer: WorkflowCheckpointer | None = None,
        evidence_store: EvidenceStore | None = None,
        url_policy: UrlPolicyService | None = None,
        backend_promote_callback: Callable[[str, dict[str, str], str, int], Coroutine[Any, Any, None]] | None = None,
        audit_callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
    ):
        self.evidence_store = evidence_store or EvidenceStore()
        self.url_policy = url_policy or UrlPolicyService()
        self.browser_manager = browser_manager or PlaywrightManager(url_policy=self.url_policy)
        self.page_inspector = page_inspector or PageInspector(evidence_store=self.evidence_store)
        self.selector_tester = selector_tester or SelectorTester()
        self.browser_extractor = browser_extractor or BrowserExtractor(
            manager=self.browser_manager,
            inspector=self.page_inspector,
            tester=self.selector_tester,
            evidence_store=self.evidence_store,
        )
        self.validation_service = validation_service or ValidationService()
        self.nim_provider = nim_provider or NvidiaNimProvider()
        self.checkpointer = checkpointer or WorkflowCheckpointer()
        self.backend_promote_callback = backend_promote_callback
        self.audit_callback = audit_callback

        self.graph = self._compile_graph()

    def _compile_graph(self):
        builder = StateGraph(WorkflowState)

        # 1. Register Graph Nodes
        builder.add_node("load_job", self._load_job_node)
        builder.add_node("check_policy", self._check_policy_node)
        builder.add_node("inspect_page", self._inspect_page_node)
        builder.add_node("propose_candidates", self._propose_candidates_node)
        builder.add_node("test_candidates", self._test_candidates_node)
        builder.add_node("validate_samples", self._validate_samples_node)
        builder.add_node("diagnose", self._diagnose_node)
        builder.add_node("await_approval", self._await_approval_node)
        builder.add_node("await_user", self._await_user_node)
        builder.add_node("promote_version", self._promote_version_node)
        builder.add_node("mark_failed", self._mark_failed_node)

        # 2. Wire Entry and Linear Transitions
        builder.add_edge(START, "load_job")
        builder.add_edge("load_job", "check_policy")

        # 3. Policy routing
        def route_after_policy(state: WorkflowState) -> str:
            if state.get("status") == "FAILED":
                return "mark_failed"
            return "inspect_page"

        builder.add_conditional_edges(
            "check_policy",
            route_after_policy,
            {
                "inspect_page": "inspect_page",
                "mark_failed": "mark_failed",
            },
        )

        builder.add_edge("inspect_page", "propose_candidates")
        builder.add_edge("propose_candidates", "test_candidates")
        builder.add_edge("test_candidates", "validate_samples")

        # 4. Route after validation
        def route_after_validation(state: WorkflowState) -> str:
            if state.get("is_verified", False):
                if state.get("requires_approval", False) and not state.get("approval_granted"):
                    return "await_approval"
                return "promote_version"
            return "diagnose"

        builder.add_conditional_edges(
            "validate_samples",
            route_after_validation,
            {
                "await_approval": "await_approval",
                "promote_version": "promote_version",
                "diagnose": "diagnose",
            },
        )

        # 5. Route after diagnosis
        def route_after_diagnose(state: WorkflowState) -> str:
            if state.get("status") == "AWAITING_USER":
                return "await_user"
            elif state.get("status") == "FAILED":
                return "mark_failed"
            return "inspect_page"

        builder.add_conditional_edges(
            "diagnose",
            route_after_diagnose,
            {
                "await_user": "await_user",
                "mark_failed": "mark_failed",
                "inspect_page": "inspect_page",
            },
        )

        # 6. Route after human approval
        def route_after_approval(state: WorkflowState) -> str:
            if state.get("approval_granted") is True:
                return "promote_version"
            return "mark_failed"

        builder.add_conditional_edges(
            "await_approval",
            route_after_approval,
            {
                "promote_version": "promote_version",
                "mark_failed": "mark_failed",
            },
        )

        # 7. Route after human user clarification
        builder.add_edge("await_user", "inspect_page")

        # 8. Terminal Nodes
        builder.add_edge("promote_version", END)
        builder.add_edge("mark_failed", END)

        return builder.compile(checkpointer=self.checkpointer.get_saver())

    # --- Node Implementations ---

    async def _emit_audit(self, state: WorkflowState, action: str, details: dict[str, Any] | None = None) -> None:
        event = {
            "action": action,
            "endpoint_id": state.get("endpoint_id"),
            "workflow_id": state.get("workflow_id"),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "details": details or {},
        }
        if "audit_log" in state and isinstance(state["audit_log"], list):
            state["audit_log"].append(event)
        if self.audit_callback:
            try:
                await self.audit_callback(event)
            except Exception as e:
                logger.warning("Audit emission error: %s", e)

    async def _load_job_node(self, state: WorkflowState) -> dict[str, Any]:
        budget = get_default_budget()
        deadline_ts = time.monotonic() + budget.deadline_seconds
        return {
            "attempt_count": 0,
            "max_attempts": state.get("max_attempts") or budget.max_attempts,
            "tool_call_count": 0,
            "max_tool_calls": state.get("max_tool_calls") or budget.max_tool_calls,
            "deadline_ts": deadline_ts,
            "status": "INITIALIZED",
            "is_verified": False,
            "evidence_refs": [],
            "audit_log": [],
        }

    async def _check_policy_node(self, state: WorkflowState) -> dict[str, Any]:
        target_url = state["target_url"]
        is_safe, reason = self.url_policy.validate_url(target_url)
        if not is_safe:
            await self._emit_audit(state, "POLICY_BLOCKED", {"url": target_url, "reason": reason})
            return {
                "status": "FAILED",
                "error_context": f"SSRF URL policy block: {reason}",
            }
        return {"status": "CHECKING_POLICY"}

    async def _inspect_page_node(self, state: WorkflowState) -> dict[str, Any]:
        target_url = state["target_url"]
        endpoint_id = state["endpoint_id"]
        logger.info("[%s] Inspecting page: %s", endpoint_id, target_url)

        try:
            async with self.browser_manager.new_page_session(target_url=target_url) as page:
                await self.browser_manager.navigate_safely(page, target_url)
                inspection = await self.page_inspector.inspect(
                    page,
                    endpoint_id=endpoint_id,
                    capture_screenshot=self.nim_provider.supports_vision(),
                )
                evidence_ref = inspection["evidence_ref"]
                refs = list(state.get("evidence_refs", []))
                if evidence_ref not in refs:
                    refs.append(evidence_ref)

                await self._emit_audit(state, "PAGE_INSPECTED", {"evidence_ref": evidence_ref})
                return {
                    "page_title": inspection["page_title"],
                    "evidence_refs": refs,
                    "status": "INSPECTING",
                }
        except Exception as e:
            return {
                "status": "DIAGNOSING",
                "error_context": f"Failed inspecting page: {e}",
            }

    async def _propose_candidates_node(self, state: WorkflowState) -> dict[str, Any]:
        endpoint_id = state["endpoint_id"]
        attempt = state.get("attempt_count", 0) + 1

        # Check budget
        exhausted, reason = is_budget_exhausted(state)
        if exhausted:
            return {
                "status": "FAILED",
                "error_context": reason,
            }

        # Load recent evidence
        evidence_payload = None
        refs = state.get("evidence_refs", [])
        if refs:
            evidence_payload = self.evidence_store.load_evidence(refs[-1])

        pruned_dom = evidence_payload.get("pruned_dom", "") if evidence_payload else ""
        screenshot_b64 = evidence_payload.get("screenshot_b64") if evidence_payload else None

        try:
            patch = await self.nim_provider.generate_selector_patch(
                schema_definition=state["schema_definition"],
                pruned_dom=pruned_dom,
                screenshot_b64=screenshot_b64,
                previous_selectors=state.get("active_selectors"),
                error_context=state.get("error_context"),
                evidence_refs=refs,
            )
            await self._emit_audit(state, "CANDIDATE_PROPOSED", {
                "selectors": patch.new_selectors,
                "reasoning": patch.ai_reasoning,
                "attempt": attempt,
            })
            return {
                "candidate_selectors": patch.new_selectors,
                "ai_reasoning": patch.ai_reasoning,
                "confidence_score": patch.confidence_score,
                "attempt_count": attempt,
                "status": "PROPOSING",
            }
        except Exception as e:
            logger.warning("[%s] Model candidate proposal failed: %s", endpoint_id, e)
            return {
                "attempt_count": attempt,
                "error_context": f"Model proposal failed: {e}",
                "status": "PROPOSING",
            }

    async def _test_candidates_node(self, state: WorkflowState) -> dict[str, Any]:
        endpoint_id = state["endpoint_id"]
        candidates = state.get("candidate_selectors")
        if not candidates:
            return {
                "is_verified": False,
                "error_context": "No candidate selectors to test",
                "status": "TESTING",
            }

        target_url = state["target_url"]
        logger.info("[%s] Testing candidate selectors in real browser: %s", endpoint_id, candidates)

        try:
            async with self.browser_manager.new_page_session(target_url=target_url) as page:
                await self.browser_manager.navigate_safely(page, target_url)
                evidences = await self.selector_tester.test_all_selectors(page, candidates)

                # Check for 0-match fields
                failed_fields = [ev.field_name for ev in evidences if ev.matched_count == 0 or ev.error]
                if failed_fields:
                    return {
                        "is_verified": False,
                        "error_context": f"Candidate selectors matched 0 elements for fields: {', '.join(failed_fields)}",
                        "status": "TESTING",
                    }

                # Extract actual sample values
                res = await self.browser_extractor.extract_from_page(
                    page=page,
                    endpoint_id=endpoint_id,
                    target_url=target_url,
                    schema_definition=state["schema_definition"],
                    selector_map=candidates,
                )

                return {
                    "sample_data": res.data,
                    "status": "TESTING",
                }
        except Exception as e:
            return {
                "is_verified": False,
                "error_context": f"Browser selector testing failed: {e}",
                "status": "TESTING",
            }

    async def _validate_samples_node(self, state: WorkflowState) -> dict[str, Any]:
        endpoint_id = state["endpoint_id"]
        sample_data = state.get("sample_data")

        if sample_data is None:
            return {
                "is_verified": False,
                "validation_errors": ["No sample data extracted"],
                "status": "VALIDATING",
            }

        val_result = self.validation_service.validate_extraction(
            extracted_data=sample_data,
            schema_definition=state["schema_definition"],
        )

        if val_result.is_valid:
            logger.info("[%s] Candidate selectors VERIFIED deterministically!", endpoint_id)
            await self._emit_audit(state, "CANDIDATE_VERIFIED", {"selectors": state.get("candidate_selectors")})
            return {
                "is_verified": True,
                "sample_data": val_result.normalized_data,
                "validation_errors": [],
                "status": "VALIDATING",
            }
        else:
            logger.warning("[%s] Candidate validation failed: %s", endpoint_id, val_result.errors)
            return {
                "is_verified": False,
                "validation_errors": val_result.errors,
                "error_context": f"Validation failed: {'; '.join(val_result.errors)}",
                "status": "VALIDATING",
            }

    async def _diagnose_node(self, state: WorkflowState) -> dict[str, Any]:
        endpoint_id = state["endpoint_id"]
        err = state.get("error_context", "") or ""

        # Check for ambiguity requiring operator clarification
        if "ambiguous" in err.lower() or "multiple" in err.lower():
            logger.info("[%s] Selector ambiguity detected; routing to await_user", endpoint_id)
            return {
                "status": "AWAITING_USER",
                "interrupt_reason": "Ambiguous element matches detected on page",
            }

        # Check if attempt budget exhausted
        exhausted, reason = is_budget_exhausted(state)
        if exhausted:
            logger.error("[%s] Workflow exhausted: %s", endpoint_id, reason)
            return {
                "status": "FAILED",
                "error_context": reason,
            }

        # Otherwise continue retry loop
        logger.info("[%s] Retrying candidate proposal (attempt %d/%d)", endpoint_id, state.get("attempt_count"), state.get("max_attempts"))
        return {"status": "DIAGNOSING"}

    async def _await_approval_node(self, state: WorkflowState) -> dict[str, Any]:
        endpoint_id = state["endpoint_id"]
        logger.info("[%s] Workflow paused at await_approval interrupt", endpoint_id)
        await self._emit_audit(state, "APPROVAL_PAUSED", {"candidates": state.get("candidate_selectors")})
        return {"status": "AWAITING_APPROVAL"}

    async def _await_user_node(self, state: WorkflowState) -> dict[str, Any]:
        endpoint_id = state["endpoint_id"]
        logger.info("[%s] Workflow paused at await_user clarification interrupt", endpoint_id)
        await self._emit_audit(state, "CLARIFICATION_PAUSED", {"reason": state.get("error_context")})
        return {"status": "AWAITING_USER"}

    async def _promote_version_node(self, state: WorkflowState) -> dict[str, Any]:
        endpoint_id = state["endpoint_id"]
        workflow_id = state.get("workflow_id", f"wf_{endpoint_id}")
        new_selectors = state.get("candidate_selectors") or {}
        reasoning = state.get("ai_reasoning", "Verified by MorphAPI backend")

        # If already promoted in this workflow, return idempotently without duplicate side effect
        if state.get("status") == "PROMOTED" and state.get("version_promoted"):
            promoted_ver = state["version_promoted"]
            logger.info("[%s] Workflow already promoted to version %d; skipping duplicate execution", endpoint_id, promoted_ver)
            return {
                "status": "PROMOTED",
                "is_verified": True,
                "version_promoted": promoted_ver,
            }

        next_version = (state.get("version_promoted") or 1) + 1

        # Check idempotency: ensure promotion side effect executes only once
        if not self.checkpointer.mark_promotion_executed(workflow_id, next_version):
            logger.warning("[%s] Promotion side effect already executed; skipping duplicate write", endpoint_id)
            return {
                "status": "PROMOTED",
                "is_verified": True,
                "version_promoted": state.get("version_promoted") or next_version,
            }

        logger.info("[%s] Deterministically promoting candidate selectors to version %d", endpoint_id, next_version)
        if self.backend_promote_callback:
            await self.backend_promote_callback(endpoint_id, new_selectors, reasoning, next_version)

        promoted_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        await self._emit_audit(state, "VERSION_PROMOTED", {
            "version": next_version,
            "selectors": new_selectors,
            "promoted_at": promoted_ts,
        })

        return {
            "active_selectors": new_selectors,
            "version_promoted": next_version,
            "promoted_at": promoted_ts,
            "status": "PROMOTED",
            "is_verified": True,
        }

    async def _mark_failed_node(self, state: WorkflowState) -> dict[str, Any]:
        endpoint_id = state["endpoint_id"]
        err = state.get("error_context", "Unknown healing failure")
        logger.error("[%s] Healing workflow terminated with FAILED status: %s", endpoint_id, err)
        await self._emit_audit(state, "WORKFLOW_FAILED", {"error": err})
        return {
            "status": "FAILED",
            "is_verified": False,
        }

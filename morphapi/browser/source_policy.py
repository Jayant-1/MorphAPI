"""
MorphAPI Responsible Access Guard & Source Policy Engine
RFC 9309 Robots Exclusion Protocol evaluator and source authorization decision gate.
Enforces deterministic ALLOW, REVIEW, and BLOCK policy outcomes before browser tools launch.
"""

import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from typing import Any

import httpx

from morphapi.browser.url_policy import UrlPolicyService
from morphapi.schemas.contracts import PolicyOutcome, SourcePolicyDecision
from morphapi.schemas.errors import SourcePolicyBlockedError

logger = logging.getLogger("morphapi.source_policy")

CRAWLER_USER_AGENT = "MorphAPIBot/1.0 (+https://morphapi.dev/bot; contact@morphapi.dev)"
CACHE_TTL_SECONDS = 3600  # 1 hour cache


class AuthorizationRepository:
    """
    Manages documented permissions and source owner authorizations.
    Permits verified integrations to proceed within an authorized scope.
    """

    def __init__(self):
        # Maps domain or url prefix to authorization record
        self._authorizations: dict[str, dict[str, Any]] = {}

    def grant_authorization(self, domain_or_url: str, scope: str = "full", authorized_by: str = "owner") -> None:
        """Records documented owner authorization for a domain or URL prefix."""
        key = domain_or_url.lower().strip()
        self._authorizations[key] = {
            "scope": scope,
            "authorized_by": authorized_by,
            "timestamp": time.time(),
        }

    def revoke_authorization(self, domain_or_url: str) -> None:
        """Revokes an authorization record."""
        key = domain_or_url.lower().strip()
        self._authorizations.pop(key, None)

    def is_authorized(self, url: str) -> tuple[bool, str | None]:
        """Checks if URL matches any active authorization records."""
        url_lower = url.lower()
        parsed = urlparse(url_lower)
        netloc = parsed.netloc

        if netloc in self._authorizations:
            auth = self._authorizations[netloc]
            return True, f"Explicit owner authorization on domain '{netloc}' (authorized by: {auth['authorized_by']})"

        for key, auth in self._authorizations.items():
            if url_lower.startswith(key):
                return True, f"Explicit owner authorization for scope '{key}' (authorized by: {auth['authorized_by']})"

        return False, None


class SourcePolicyService:
    """
    MorphAPI Responsible Access Guard.
    Fetches, parses, and deterministically evaluates robots.txt rules,
    source authorizations, and network safety before any browser tool executes.
    """

    def __init__(
        self,
        url_policy: UrlPolicyService | None = None,
        auth_repo: AuthorizationRepository | None = None,
        http_timeout_seconds: float = 6.0,
    ):
        self.url_policy = url_policy or UrlPolicyService()
        self.auth_repo = auth_repo or AuthorizationRepository()
        self.http_timeout = http_timeout_seconds
        # In-memory cache: netloc -> (RobotFileParser | None, timestamp, status_code)
        self._cache: dict[str, tuple[RobotFileParser | None, float, int]] = {}

    async def evaluate_url(self, url: str) -> SourcePolicyDecision:
        """
        Deterministically evaluates policy rules for a target URL.
        Returns SourcePolicyDecision with ALLOW, REVIEW, or BLOCK.
        """
        # 1. URL Safety & SSRF Gate
        is_safe, ssrf_reason = self.url_policy.validate_url(url)
        if not is_safe:
            logger.warning("[Access Guard] [BLOCK] URL safety check failed for %s: %s", url, ssrf_reason)
            return SourcePolicyDecision(
                url=url,
                outcome=PolicyOutcome.BLOCK,
                robots_allowed=False,
                reason=f"URL safety policy violation: {ssrf_reason}",
                evidence_urls=[],
                requires_human_review=False,
            )

        # 2. Check Documented Owner Authorization
        is_auth, auth_reason = self.auth_repo.is_authorized(url)
        if is_auth:
            logger.info("[Access Guard] [ALLOW] %s granted by authorization repository: %s", url, auth_reason)
            return SourcePolicyDecision(
                url=url,
                outcome=PolicyOutcome.ALLOW,
                robots_allowed=True,
                reason=auth_reason or "Documented owner authorization present",
                evidence_urls=[],
                requires_human_review=False,
            )

        # 3. Retrieve and Evaluate robots.txt (RFC 9309)
        parsed = urlparse(url)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        robots_url = f"{scheme}://{netloc}/robots.txt"

        rp, status_code = await self._get_robot_parser(robots_url, netloc)

        # RFC 9309 section 2.3.1.2: 404/410 means crawlers may access all resources
        if status_code in (404, 410):
            logger.info("[Access Guard] [ALLOW] %s - No robots.txt found (HTTP %d). Access permitted.", url, status_code)
            return SourcePolicyDecision(
                url=url,
                outcome=PolicyOutcome.ALLOW,
                robots_allowed=True,
                reason=f"No robots.txt restrictions found on '{netloc}' (HTTP {status_code}). Crawling permitted under RFC 9309.",
                evidence_urls=[robots_url],
                requires_human_review=False,
            )

        # Unavailable / Network Error / 5xx Server Error -> Fail Closed / Review
        if rp is None or status_code >= 500 or status_code == 0:
            logger.warning("[Access Guard] [REVIEW] %s - robots.txt unavailable (status: %d). Requiring review.", url, status_code)
            return SourcePolicyDecision(
                url=url,
                outcome=PolicyOutcome.REVIEW,
                robots_allowed=None,
                reason=f"robots.txt on '{netloc}' could not be retrieved reliably (HTTP status: {status_code}). Fail-closed policy requires operator review.",
                evidence_urls=[robots_url],
                requires_human_review=True,
            )

        # Evaluate path rules for both MorphAPIBot and generic crawler (*)
        bot_allowed = rp.can_fetch("MorphAPIBot", url)
        star_allowed = rp.can_fetch("*", url)

        # If either explicitly disallows our bot or all bots
        if not bot_allowed or not star_allowed:
            logger.info("[Access Guard] [BLOCK] %s - Disallowed by robots.txt rules for user-agent * or MorphAPIBot", url)
            return SourcePolicyDecision(
                url=url,
                outcome=PolicyOutcome.BLOCK,
                robots_allowed=False,
                reason=f"The requested path '{path}' is disallowed by {netloc}/robots.txt rules for crawler identity.",
                evidence_urls=[robots_url],
                requires_human_review=False,
            )

        logger.info("[Access Guard] [ALLOW] %s - Permitted by robots.txt rules on %s", url, netloc)
        return SourcePolicyDecision(
            url=url,
            outcome=PolicyOutcome.ALLOW,
            robots_allowed=True,
            reason=f"Robots exclusion protocol rules on '{netloc}' permit automated access to '{path}'.",
            evidence_urls=[robots_url],
            requires_human_review=False,
        )

    async def enforce_policy(self, url: str) -> SourcePolicyDecision:
        """
        Enforces access policy at the backend boundary.
        Raises SourcePolicyBlockedError if the request outcome is BLOCK.
        """
        decision = await self.evaluate_url(url)
        if decision.outcome == PolicyOutcome.BLOCK:
            raise SourcePolicyBlockedError(
                message=f"Responsible Access Guard blocked access to '{url}': {decision.reason}",
                details=decision.model_dump(),
            )
        return decision

    async def _get_robot_parser(self, robots_url: str, netloc: str) -> tuple[RobotFileParser | None, int]:
        """Fetches and parses robots.txt with in-memory caching."""
        now = time.time()
        if netloc in self._cache:
            cached_rp, cached_ts, cached_status = self._cache[netloc]
            if now - cached_ts < CACHE_TTL_SECONDS:
                return cached_rp, cached_status

        # Validate robots URL against SSRF
        is_safe, _ = self.url_policy.validate_url(robots_url)
        if not is_safe:
            return None, 403

        headers = {
            "User-Agent": CRAWLER_USER_AGENT,
            "Accept": "text/plain, */*",
        }

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout, follow_redirects=True) as client:
                resp = await client.get(robots_url, headers=headers)
                status = resp.status_code

                if status == 200:
                    text = resp.text
                    rp = RobotFileParser()
                    rp.parse(text.splitlines())
                    self._cache[netloc] = (rp, now, status)
                    return rp, status
                elif status in (404, 410):
                    self._cache[netloc] = (None, now, status)
                    return None, status
                else:
                    self._cache[netloc] = (None, now, status)
                    return None, status
        except Exception as e:
            logger.warning("[Access Guard] Error fetching robots.txt from %s: %s", robots_url, e)
            self._cache[netloc] = (None, now, 0)
            return None, 0


# Global singleton instance
source_policy_service = SourcePolicyService()

"""
Tests for MorphAPI Responsible Access Guard & Source Policy Engine
Verifies deterministic ALLOW, REVIEW, and BLOCK outcomes and RFC 9309 rules.
"""

import pytest
from unittest.mock import AsyncMock, patch
from urllib.robotparser import RobotFileParser

from morphapi.browser.source_policy import AuthorizationRepository, SourcePolicyService
from morphapi.browser.url_policy import UrlPolicyService
from morphapi.schemas.contracts import PolicyOutcome
from morphapi.schemas.errors import SourcePolicyBlockedError


@pytest.fixture
def auth_repo():
    return AuthorizationRepository()


@pytest.fixture
def url_policy():
    return UrlPolicyService(allow_local=False)


@pytest.fixture
def policy_service(url_policy, auth_repo):
    return SourcePolicyService(url_policy=url_policy, auth_repo=auth_repo)


SAMPLE_ROBOTS_TXT = """
User-agent: *
Disallow: /private/
Disallow: /admin/
Disallow: /account/
Allow: /products/
Allow: /wiki/List_of_
"""


@pytest.mark.asyncio
async def test_robots_allowed_path(policy_service):
    """Test that allowed paths yield PolicyOutcome.ALLOW."""
    rp = RobotFileParser()
    rp.parse(SAMPLE_ROBOTS_TXT.splitlines())

    with patch.object(policy_service, "_get_robot_parser", new=AsyncMock(return_value=(rp, 200))):
        decision = await policy_service.evaluate_url("https://example.com/products/vegetables")
        assert decision.outcome == PolicyOutcome.ALLOW
        assert decision.robots_allowed is True
        assert "permit automated access" in decision.reason


@pytest.mark.asyncio
async def test_robots_disallowed_path(policy_service):
    """Test that disallowed paths yield PolicyOutcome.BLOCK."""
    rp = RobotFileParser()
    rp.parse(SAMPLE_ROBOTS_TXT.splitlines())

    with patch.object(policy_service, "_get_robot_parser", new=AsyncMock(return_value=(rp, 200))):
        decision = await policy_service.evaluate_url("https://example.com/private/prices")
        assert decision.outcome == PolicyOutcome.BLOCK
        assert decision.robots_allowed is False
        assert "disallowed by example.com/robots.txt" in decision.reason


@pytest.mark.asyncio
async def test_robots_not_found_404_allows_access(policy_service):
    """RFC 9309 2.3.1.2: 404 Not Found means crawlers may access all resources."""
    with patch.object(policy_service, "_get_robot_parser", new=AsyncMock(return_value=(None, 404))):
        decision = await policy_service.evaluate_url("https://example.com/any/path")
        assert decision.outcome == PolicyOutcome.ALLOW
        assert decision.robots_allowed is True
        assert "No robots.txt restrictions" in decision.reason


@pytest.mark.asyncio
async def test_robots_unavailable_500_requires_review(policy_service):
    """Fail-closed policy requires operator review when robots.txt cannot be fetched reliably."""
    with patch.object(policy_service, "_get_robot_parser", new=AsyncMock(return_value=(None, 500))):
        decision = await policy_service.evaluate_url("https://example.com/data")
        assert decision.outcome == PolicyOutcome.REVIEW
        assert decision.robots_allowed is None
        assert decision.requires_human_review is True
        assert "Fail-closed policy requires operator review" in decision.reason


@pytest.mark.asyncio
async def test_ssrf_and_private_network_blocked(policy_service):
    """SSRF and local IP addresses are blocked before robots.txt check."""
    decision = await policy_service.evaluate_url("http://169.254.169.254/latest/meta-data/")
    assert decision.outcome == PolicyOutcome.BLOCK
    assert decision.robots_allowed is False
    assert "URL safety policy violation" in decision.reason


@pytest.mark.asyncio
async def test_owner_authorization_override(policy_service, auth_repo):
    """Documented owner authorization permits extraction even if robots would disallow."""
    rp = RobotFileParser()
    rp.parse(SAMPLE_ROBOTS_TXT.splitlines())

    # Register verified owner authorization
    auth_repo.grant_authorization("example.com", authorized_by="Site Owner Jane")

    decision = await policy_service.evaluate_url("https://example.com/private/prices")
    assert decision.outcome == PolicyOutcome.ALLOW
    assert "Explicit owner authorization" in decision.reason
    assert "Site Owner Jane" in decision.reason


@pytest.mark.asyncio
async def test_enforce_policy_raises_on_block(policy_service):
    """enforce_policy raises SourcePolicyBlockedError when outcome is BLOCK."""
    rp = RobotFileParser()
    rp.parse(SAMPLE_ROBOTS_TXT.splitlines())

    with patch.object(policy_service, "_get_robot_parser", new=AsyncMock(return_value=(rp, 200))):
        with pytest.raises(SourcePolicyBlockedError) as exc_info:
            await policy_service.enforce_policy("https://example.com/admin/settings")
        assert "Responsible Access Guard blocked access" in str(exc_info.value)

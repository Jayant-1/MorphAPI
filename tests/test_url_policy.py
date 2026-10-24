"""
Unit & Contract Tests for URL Policy, SSRF Protection, and Sanitization
"""

import pytest
from morphapi.browser.url_policy import (
    UrlPolicyService,
    validate_selector_safety,
    sanitize_text_for_llm,
)
from morphapi.schemas.errors import SsrfSecurityError


def test_ssrf_blocks_private_and_loopback_ips(strict_url_policy):
    prohibited_ips = [
        "127.0.0.1",
        "10.0.0.1",
        "192.168.1.1",
        "172.16.0.1",
        "169.254.169.254",   # Cloud metadata
        "100.100.100.200",   # Cloud metadata
        "100.64.0.1",        # Carrier Grade NAT
        "0.0.0.0",
        "::1",               # IPv6 loopback
    ]
    for ip in prohibited_ips:
        is_allowed, reason = strict_url_policy.is_ip_allowed(ip)
        assert not is_allowed, f"IP '{ip}' should be blocked, but was allowed"
        assert reason is not None


def test_ssrf_allows_public_ips(strict_url_policy):
    public_ips = [
        "8.8.8.8",
        "1.1.1.1",
        "142.250.190.46",
    ]
    for ip in public_ips:
        is_allowed, reason = strict_url_policy.is_ip_allowed(ip)
        assert is_allowed, f"Public IP '{ip}' should be allowed: {reason}"


def test_ssrf_allow_local_flag(local_url_policy):
    is_allowed, reason = local_url_policy.is_ip_allowed("127.0.0.1")
    assert is_allowed
    is_allowed, reason = local_url_policy.is_ip_allowed("192.168.1.1")
    assert is_allowed


def test_validate_url_prohibited_schemes(strict_url_policy):
    prohibited = [
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<html></html>",
        "ftp://example.com/file.txt",
    ]
    for url in prohibited:
        is_valid, reason = strict_url_policy.validate_url(url)
        assert not is_valid
        assert "scheme" in reason.lower()


def test_validate_url_blocks_localhost_by_default(strict_url_policy):
    is_valid, reason = strict_url_policy.validate_url("http://localhost:8000/api")
    assert not is_valid
    assert "localhost" in reason.lower()

    with pytest.raises(SsrfSecurityError):
        strict_url_policy.enforce_url_policy("http://localhost:8000/api")


def test_validate_selector_safety():
    # Safe selectors
    safe_selectors = [
        ".product-title",
        "#price",
        "table.data-table > tr > td.price",
        "//div[@class='item']/span[1]",
        "h1.heading",
        "[data-test='product-name']",
    ]
    for sel in safe_selectors:
        is_safe, err = validate_selector_safety(sel)
        assert is_safe, f"Selector '{sel}' should be safe: {err}"

    # Dangerous injection selectors
    dangerous_selectors = [
        "javascript:alert(document.cookie)",
        "<script>fetch('http://attacker.com')</script>",
        "div[onclick='eval(code)']",
        "expression(alert('xss'))",
        "data:text/html;base64,PHNjcmlwdD4=",
        "",
        "   ",
    ]
    for sel in dangerous_selectors:
        is_safe, err = validate_selector_safety(sel)
        assert not is_safe, f"Selector '{sel}' should be flagged as unsafe"


def test_sanitize_text_redacts_credentials():
    text_with_secrets = (
        "Here is the API key: nvapi-abcdef1234567890abcdef1234567890 and "
        "Authorization: Bearer my_secret_token_123456789 and "
        "password='super_secret_password_here' inside the DOM"
    )
    sanitized = sanitize_text_for_llm(text_with_secrets, max_chars=1000)
    assert "nvapi-" not in sanitized
    assert "super_secret_password_here" not in sanitized
    assert "[REDACTED_CREDENTIAL]" in sanitized


def test_sanitize_text_truncates_large_payload():
    large_text = "A" * 60000
    sanitized = sanitize_text_for_llm(large_text, max_chars=50000)
    assert len(sanitized) <= 50100
    assert "[TRUNCATED_FOR_SIZE]" in sanitized

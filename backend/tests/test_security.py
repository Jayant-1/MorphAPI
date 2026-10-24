"""
Tests for security: SSRF blocking, prohibited schemes, selector safety, and secret redaction.
"""

from backend.app.services.security import (
    validate_url_ssrf,
    validate_selector_safety,
    sanitize_text_for_llm,
    is_ip_restricted,
)


def test_ssrf_blocks_private_ips():
    assert is_ip_restricted("10.0.0.1") is True
    assert is_ip_restricted("192.168.1.1") is True
    assert is_ip_restricted("172.16.0.1") is True
    assert is_ip_restricted("127.0.0.1") is True


def test_ssrf_blocks_cloud_metadata():
    assert is_ip_restricted("169.254.169.254") is True


def test_ssrf_allow_local_flag():
    # When allow_local is True, 127.0.0.1 is permitted
    assert is_ip_restricted("127.0.0.1", allow_local=True) is False
    # But metadata IPs are still strictly blocked even with allow_local=True
    assert is_ip_restricted("169.254.169.254", allow_local=True) is True


def test_validate_url_ssrf_prohibited_schemes():
    valid, err = validate_url_ssrf("file:///etc/passwd")
    assert valid is False
    assert "scheme" in err.lower()

    valid, err = validate_url_ssrf("javascript:alert(1)")
    assert valid is False

    valid, err = validate_url_ssrf("ftp://example.com/data")
    assert valid is False


def test_validate_url_ssrf_blocks_localhost_by_default():
    valid, err = validate_url_ssrf("http://localhost:8000/api")
    assert valid is False
    assert "localhost" in err.lower()


def test_validate_selector_safety():
    # Safe selectors
    assert validate_selector_safety("div.crop-card span.price")[0] is True
    assert validate_selector_safety("//table[@id='data']//tr/td[1]")[0] is True
    assert validate_selector_safety("tr:nth-child(2) > td.val")[0] is True

    # Dangerous script injection / function calls
    assert validate_selector_safety("javascript:alert(1)")[0] is False
    assert validate_selector_safety("<script>alert('xss')</script>")[0] is False
    assert validate_selector_safety("div[onload='evil()']")[0] is False
    assert validate_selector_safety("div:eval('document.cookie')")[0] is False


def test_sanitize_text_for_llm_redacts_tokens():
    text_with_jwt = "User token is eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sometesttoken12345"
    sanitized = sanitize_text_for_llm(text_with_jwt)
    assert "eyJhbGciOiJIUzI1Ni" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized

    text_with_auth = 'Authorization: Bearer sk-antigravity-secret-token-abcdef123456789'
    sanitized_auth = sanitize_text_for_llm(text_with_auth)
    assert "sk-antigravity-secret" not in sanitized_auth
    assert "[REDACTED_SECRET]" in sanitized_auth

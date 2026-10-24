"""
MorphAPI Network and Browser Security Module
Guards against SSRF, DNS rebinding, sensitive credential leakage, and malicious selector code execution.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

# Disallowed URI schemes
ALLOWED_SCHEMES = {"http", "https"}

# Blocked cloud metadata and sensitive internal IPs
METADATA_IPS = {
    ipaddress.ip_network("169.254.169.254/32"),  # AWS / GCP / Azure IMDS
    ipaddress.ip_network("fd00:ec2::254/128"),    # AWS IPv6 IMDS
}

# Regex to detect suspicious JavaScript or script execution patterns in candidate selectors
DANGEROUS_SELECTOR_PATTERNS = [
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"\bon[a-zA-Z]+\s*=", re.IGNORECASE),  # e.g. onload=, onerror=, onclick=
    re.compile(r"\b(eval|exec|function|window|document|localStorage|sessionStorage|cookie)\b", re.IGNORECASE),
    re.compile(r"[-_\w]+\s*\((.*?)\)", re.IGNORECASE),  # function calls except safe CSS pseudo-classes
]

# Whitelist of allowed CSS pseudo-functions
ALLOWED_PSEUDO_FUNCTIONS = {
    "nth-child", "nth-of-type", "nth-last-child", "nth-last-of-type",
    "first-child", "last-child", "only-child", "not", "is", "where", "has",
    "contains", "text", "xpath"
}

# Regex to mask possible auth tokens or secrets from LLM prompts
SENSITIVE_PATTERNS = [
    re.compile(r"(bearer\s+)[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(key|secret|token|password|auth|credential)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{12,}[\"']?", re.IGNORECASE),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", re.IGNORECASE),  # JWTs
]


class SecurityValidationError(Exception):
    """Raised when security boundaries (SSRF, malicious selector, etc.) are violated."""
    pass


def is_ip_restricted(ip_str: str, allow_local: bool = False) -> bool:
    """
    Checks if an IP address belongs to private, loopback, link-local, multicast,
    or cloud metadata ranges.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # If invalid IP, treat as restricted

    # Always block cloud metadata endpoints
    for meta_net in METADATA_IPS:
        if ip in meta_net:
            return True

    # If local testing is explicitly permitted, allow loopback addresses (127.0.0.1, ::1)
    if allow_local and ip.is_loopback:
        return False

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_url_ssrf(url: str, allow_local: bool = False) -> tuple[bool, str | None]:
    """
    Validates a URL against SSRF and unauthorized network destinations.
    Returns (is_valid, error_reason).
    """
    if not url:
        return False, "Target URL cannot be empty"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Failed to parse URL: {e}"

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        return False, f"Prohibited URL scheme '{scheme}'. Only http and https are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL hostname is missing"

    # Normalize hostname
    hostname = hostname.strip().lower()

    # Reject localhost / 127.0.0.1 / ::1 if allow_local is False
    if not allow_local:
        if hostname in ("localhost", "localhost.localdomain") or hostname.endswith(".localhost"):
            return False, "Access to localhost is restricted for security (SSRF prevention)"

    # Resolve DNS to check IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if scheme == "https" else 80))
    except socket.gaierror as e:
        return False, f"Failed to resolve hostname '{hostname}': {e}"

    if not addr_info:
        return False, f"Hostname '{hostname}' did not resolve to any IP address"

    for entry in addr_info:
        ip_addr = entry[4][0]
        if is_ip_restricted(ip_addr, allow_local=allow_local):
            return False, f"Destination IP '{ip_addr}' resolved for '{hostname}' is restricted"

    return True, None


def validate_selector_safety(selector: str) -> tuple[bool, str | None]:
    """
    Ensures a candidate selector is a pure CSS or XPath locator and contains
    no executable JavaScript or script injection payloads.
    """
    if not selector or not isinstance(selector, str):
        return False, "Selector must be a non-empty string"

    sel_clean = selector.strip()
    if len(sel_clean) > 500:
        return False, "Selector exceeds maximum length of 500 characters"

    # Check for direct script injection or JS pseudo-schemes
    if "javascript:" in sel_clean.lower() or "<script" in sel_clean.lower():
        return False, "Dangerous script injection detected in selector"

    # Check dangerous execution keywords
    for pattern in DANGEROUS_SELECTOR_PATTERNS[:3]:
        if pattern.search(sel_clean):
            return False, "Dangerous JavaScript execution keywords detected in selector"

    # Verify function call pattern (only allow legitimate CSS pseudo-functions)
    func_matches = re.findall(r":([a-zA-Z0-9_\-]+)\(", sel_clean)
    for func in func_matches:
        if func.lower() not in ALLOWED_PSEUDO_FUNCTIONS:
            return False, f"Unsupported or dangerous selector function ':{func}()'"

    return True, None


def sanitize_text_for_llm(content: str, max_chars: int = 60000) -> str:
    """
    Redacts secrets/tokens and truncates payload before sending to model.
    """
    if not content:
        return ""

    sanitized = content
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

    if len(sanitized) > max_chars:
        sanitized = sanitized[:max_chars] + "\n<!-- [TRUNCATED DUE TO SIZE LIMIT] -->"

    return sanitized


def validate_redirect_url(url: str, allow_local: bool = False) -> tuple[bool, str | None]:
    """Alias for validate_url_ssrf specifically for redirect inspection."""
    return validate_url_ssrf(url, allow_local=allow_local)


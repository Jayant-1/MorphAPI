"""
MorphAPI URL Policy & Security Guardrails
Defends against SSRF, private/loopback network access, cloud metadata endpoints,
DNS rebinding, malicious redirects, and dangerous selector injections.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse
from typing import Tuple, Any

from morphapi.schemas.errors import FailureCode, SsrfSecurityError

# Cloud metadata addresses to explicitly block
METADATA_IPS = {
    "169.254.169.254",   # AWS / GCP / Azure metadata
    "metadata.google.internal",
    "100.100.100.200",   # Alibaba cloud metadata
    "192.0.0.192",       # Oracle cloud metadata
}

# Dangerous selector patterns
DANGEROUS_SELECTOR_PATTERNS = [
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
]

# Sensitive token redaction regexes
TOKEN_PATTERNS = [
    re.compile(r"nvapi-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"(?:bearer\s+|api[_-]?key[\s:=]+)([A-Za-z0-9_\-\.]{16,})", re.IGNORECASE),
    re.compile(r"(?:password|secret)[\s:=]+['\"]?([^'\"\s]+)", re.IGNORECASE),
]


class UrlPolicyService:
    """
    Evaluates URLs and redirects for security compliance before and during browser navigation.
    """

    def __init__(self, allow_local: bool = False):
        self.allow_local = allow_local

    def is_ip_allowed(self, ip_str: str) -> Tuple[bool, str | None]:
        """
        Validates if an IP address is safe for outbound navigation.
        Blocks private, loopback, link-local, reserved, and cloud metadata addresses.
        """
        if self.allow_local:
            return True, None

        if ip_str in METADATA_IPS:
            return False, f"Access to cloud metadata service IP '{ip_str}' is strictly prohibited"

        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Invalid IP address format: '{ip_str}'"

        if ip.is_loopback:
            return False, f"Access to loopback IP '{ip_str}' is prohibited"

        if ip.is_private:
            return False, f"Access to private RFC1918 / RFC4193 network IP '{ip_str}' is prohibited"

        if ip.is_link_local:
            return False, f"Access to link-local IP '{ip_str}' is prohibited"

        if ip.is_reserved:
            return False, f"Access to reserved IP range '{ip_str}' is prohibited"

        if ip.is_multicast:
            return False, f"Access to multicast IP '{ip_str}' is prohibited"

        # Check for carrier-grade NAT 100.64.0.0/10
        if isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False, f"Access to Shared Address Space (CGNAT) '{ip_str}' is prohibited"

        return True, None

    def validate_url(self, url_str: str) -> Tuple[bool, str | None]:
        """
        Validates scheme and resolves hostname to ensure destination IP is safe.
        """
        try:
            parsed = urlparse(url_str)
        except Exception as e:
            return False, f"Malformed URL syntax: {e}"

        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"Prohibited URL scheme '{parsed.scheme}'. Only 'http' and 'https' are permitted."

        hostname = parsed.hostname
        if not hostname:
            return False, "URL missing hostname"

        if hostname.lower() in METADATA_IPS or hostname.lower() in ("localhost", "localhost.localdomain"):
            if not self.allow_local:
                return False, f"Prohibited hostname: '{hostname}'"

        # Perform DNS resolution and verify all returned IP addresses
        try:
            addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            return False, f"DNS resolution failed for '{hostname}': {e}"

        resolved_ips = {item[4][0] for item in addr_info}
        for ip in resolved_ips:
            is_allowed, reason = self.is_ip_allowed(ip)
            if not is_allowed:
                return False, f"Destination resolved to prohibited IP '{ip}': {reason}"

        return True, None

    def enforce_url_policy(self, url_str: str) -> None:
        """Raises SsrfSecurityError if URL fails security policy."""
        is_safe, reason = self.validate_url(url_str)
        if not is_safe:
            raise SsrfSecurityError(f"URL policy violation: {reason}", details={"url": url_str})


def validate_selector_safety(selector: str) -> Tuple[bool, str | None]:
    """
    Validates that a CSS or XPath selector does not contain script injections or dangerous payloads.
    """
    if not selector or not isinstance(selector, str) or not selector.strip():
        return False, "Selector cannot be empty"

    for pattern in DANGEROUS_SELECTOR_PATTERNS:
        if pattern.search(selector):
            return False, f"Dangerous selector pattern detected: '{pattern.pattern}'"

    return True, None


def sanitize_text_for_llm(raw_text: str, max_chars: int = 50000) -> str:
    """
    Redacts credentials and limits text size to avoid prompt-context exhaustion.
    """
    sanitized = raw_text
    for pattern in TOKEN_PATTERNS:
        sanitized = pattern.sub("[REDACTED_CREDENTIAL]", sanitized)

    if len(sanitized) > max_chars:
        sanitized = sanitized[:max_chars] + "\n...[TRUNCATED_FOR_SIZE]"

    return sanitized


def resolve_test_url(target_url: str, inputs: dict[str, Any] | None = None) -> str:
    """
    Universally resolves parameterized target URL templates for live browser verification.
    Substitutes defaults from inputs metadata if available, cleans empty query filter placeholders,
    and defaults pagination path segments to '1' without any hardcoded domain logic.
    """
    from urllib.parse import unquote, urlparse, parse_qs, urlencode, urlunparse
    import re

    # Unquote URL-encoded braces (e.g. %7Bpage%7D -> {page})
    url = unquote(target_url)

    # 1. Substitute explicit default values from inputs definition if present
    if inputs and isinstance(inputs, dict):
        for param_name, param_meta in inputs.items():
            if isinstance(param_meta, dict):
                def_val = param_meta.get("default")
                if def_val is not None:
                    url = re.sub(rf"\{{{param_name}\}}", str(def_val), url, flags=re.IGNORECASE)

    # 2. For remaining query placeholders (e.g. ?batch={batch} or &filter={x}), strip empty filter params
    parsed = urlparse(url)
    if "{" in parsed.query and "}" in parsed.query:
        qs = parse_qs(parsed.query)
        clean_qs = {k: [v for v in vals if "{" not in v] for k, vals in qs.items()}
        clean_qs = {k: v for k, v in clean_qs.items() if v}
        new_query = urlencode(clean_qs, doseq=True)
        url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    # 3. For remaining path placeholders (e.g. /page/{page}/ or page-{page}.html)
    if "{" in url and "}" in url:
        url = re.sub(r"page[-_]\{[a-zA-Z0-9_]+\}\.html", "page-1.html", url, flags=re.IGNORECASE)
        url = re.sub(r"page[-_/]\{[a-zA-Z0-9_]+\}", "page/1", url, flags=re.IGNORECASE)
        url = re.sub(r"\{(?:page|p|page_num|pg|offset|num|index|start)\}", "1", url, flags=re.IGNORECASE)
        url = re.sub(r"\{[a-zA-Z0-9_]+\}", "", url)

    # Clean redundant double slashes in path (e.g. com//page/1/ -> com/page/1/)
    parsed = urlparse(url)
    clean_path = re.sub(r"/+", "/", parsed.path)
    url = urlunparse((parsed.scheme, parsed.netloc, clean_path, parsed.params, parsed.query, parsed.fragment))

    return url


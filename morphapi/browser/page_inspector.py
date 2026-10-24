"""
MorphAPI Page Inspector & DOM Pruner
Extracts structural DOM representations, captures sanitized visual evidence,
prunes non-structural tags (scripts, styles, SVGs), and manages durable evidence references.
"""

import base64
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup, Comment
from playwright.async_api import Page

from morphapi.config import settings
from morphapi.browser.url_policy import sanitize_text_for_llm

logger = logging.getLogger("morphapi.inspector")

STRIP_TAGS = {
    "script", "style", "noscript", "svg", "iframe", "canvas",
    "audio", "video", "source", "track", "map", "object", "embed",
    "nav", "aside", "footer", "header",
}

PRESERVE_ATTRS = {
    "id", "class", "name", "role", "href", "src", "title", "alt",
    "type", "value", "placeholder", "aria-label", "aria-labelledby",
}


def prune_dom(html_content: str, max_chars: int = 60000) -> str:
    """
    Prunes HTML document to semantic structural skeleton.
    Removes script, style, SVG, base64 blobs, comments, and empty wrappers.
    Retains layout hierarchy and identifying attributes.
    """
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Remove comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # 2. Decompose blacklisted tags
    for tag_name in STRIP_TAGS:
        for elem in soup.find_all(tag_name):
            elem.decompose()

    # 2b. Decompose navigation chrome containers and boilerplate UI
    for elem in soup.find_all(True):
        if elem.name not in ("html", "body", "main") and elem.attrs and elem.parent:
            cls_lower = [c.lower() for c in (elem.get("class") or [])]
            id_lower = str(elem.get("id") or "").lower()
            if any(k in id_lower for k in ["sidebar", "mw-navigation", "vector-header", "vector-page-toolbar"]) or \
               any(k in c for c in cls_lower for k in ["sidebar", "mw-navigation", "vector-page-toolbar", "mw-portlet", "vector-dropdown", "vector-toc", "breadcrumb", "breadcrumbs", "cookie-banner"]):
                elem.decompose()

    # 3. Strip non-essential attributes
    for elem in soup.find_all(True):
        attrs = dict(elem.attrs)
        new_attrs = {}
        for k, v in attrs.items():
            k_lower = k.lower()
            if k_lower in PRESERVE_ATTRS or k_lower.startswith("data-"):
                if isinstance(v, list):
                    v = " ".join(v)
                # Strip long base64 or inline data values
                if isinstance(v, str) and (v.startswith("data:") or len(v) > 200):
                    v = v[:50] + "...[TRUNCATED]"
                new_attrs[k] = v
        elem.attrs = new_attrs

    # 4. Convert to string focusing on primary data content if present
    content_root = soup.find(["main", "article"]) or soup.find(id="content") or soup
    raw_pruned = str(content_root)
    collapsed = re.sub(r"[ \t]+", " ", raw_pruned)
    collapsed = re.sub(r"\n\s*\n+", "\n", collapsed).strip()

    # 5. Redact credentials and enforce max size limit
    return sanitize_text_for_llm(collapsed, max_chars=max_chars)


class EvidenceStore:
    """
    Persists large sanitized page evidence to local files,
    allowing LangGraph workflow state to store lightweight references rather than unbounded DOM dumps.
    """

    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = Path(storage_dir or settings.evidence_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_evidence(self, endpoint_id: str, payload: dict[str, Any]) -> str:
        """Stores evidence payload and returns an evidence reference ID."""
        content_json = json.dumps(payload, default=str)
        ref_hash = hashlib.sha256(content_json.encode("utf-8")).hexdigest()[:16]
        evidence_ref = f"ev_{endpoint_id}_{ref_hash}"
        file_path = self.storage_dir / f"{evidence_ref}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_json)

        return evidence_ref

    def load_evidence(self, evidence_ref: str) -> dict[str, Any] | None:
        file_path = self.storage_dir / f"{evidence_ref}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)


class PageInspector:
    """
    Inspects rendered pages, extracts structural DOM skeletons,
    captures screenshots when requested, and records evidence references.
    """

    def __init__(self, evidence_store: EvidenceStore | None = None):
        self.evidence_store = evidence_store or EvidenceStore()

    async def inspect(
        self,
        page: Page,
        endpoint_id: str = "default",
        capture_screenshot: bool = True,
    ) -> dict[str, Any]:
        """
        Inspects live rendered page and returns sanitized metadata and evidence reference.
        """
        title = await page.title()
        current_url = page.url
        raw_html = await page.content()
        pruned = prune_dom(raw_html)

        screenshot_b64: str | None = None
        if capture_screenshot:
            try:
                screenshot_bytes = await page.screenshot(type="png", full_page=False)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
            except Exception as e:
                logger.warning("Failed to capture screenshot: %s", e)

        # Store in durable evidence repository
        evidence_payload = {
            "endpoint_id": endpoint_id,
            "url": current_url,
            "page_title": title,
            "pruned_dom": pruned,
            "screenshot_b64": screenshot_b64,
        }
        evidence_ref = self.evidence_store.save_evidence(endpoint_id, evidence_payload)

        return {
            "evidence_ref": evidence_ref,
            "page_title": title,
            "current_url": current_url,
            "pruned_dom": pruned,
            "screenshot_b64": screenshot_b64,
        }

    async def inspect_element_context(
        self,
        page: Page,
        region_hint: str | None = None,
    ) -> str:
        """
        Returns focused DOM HTML around a selector or region hint.
        """
        if not region_hint:
            content = await page.content()
            return prune_dom(content, max_chars=10000)

        try:
            locator = page.locator(region_hint).first
            if await locator.count() > 0:
                inner_html = await locator.inner_html()
                return prune_dom(inner_html, max_chars=10000)
        except Exception as e:
            logger.debug("Failed locating region_hint '%s': %s", region_hint, e)

        content = await page.content()
        return prune_dom(content, max_chars=10000)

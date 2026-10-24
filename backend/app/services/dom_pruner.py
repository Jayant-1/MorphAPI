"""
MorphAPI DOM Pruner
Extracts the meaningful semantic and structural DOM skeleton needed by the LLM
to discover or heal CSS/XPath selectors, discarding noise (scripts, styles, large base64, tracking pixels).
Aims for >=80% character reduction while preserving table rows, labels, headers, and element identifiers.
"""

import re
from bs4 import BeautifulSoup, Comment

# Tags that never contain useful visual or structural scraping targets
DISCARD_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "path",
    "canvas",
    "video",
    "audio",
    "iframe",
    "object",
    "embed",
    "meta",
    "link",
}

# Attributes to keep for selector synthesis
KEEP_ATTRIBUTES = {
    "id",
    "class",
    "name",
    "role",
    "aria-label",
    "aria-labelledby",
    "title",
    "data-testid",
    "data-id",
    "data-field",
    "type",
    "href",
    "src",
    "placeholder",
    "value",
}


def prune_dom(html_content: str, max_chars: int = 60000) -> str:
    """
    Prunes an HTML document into a concise structural representation.
    Returns cleaned HTML string.
    """
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Remove comments
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    # 2. Remove discarded noisy tags
    for tag in soup.find_all(DISCARD_TAGS):
        tag.decompose()

    # 3. Clean attributes on remaining tags
    for tag in soup.find_all(True):
        attrs = dict(tag.attrs)
        for attr in list(attrs.keys()):
            if attr.lower() not in KEEP_ATTRIBUTES:
                del tag[attr]
            else:
                val = tag[attr]
                if isinstance(val, list):
                    val = " ".join(val)
                # Remove long data URIs or base64 blobs
                if isinstance(val, str) and (val.startswith("data:") or len(val) > 120):
                    tag[attr] = val[:100] + "..."

    # 4. Serialize cleaned DOM
    pruned = soup.prettify()

    # Collapse excessive blank lines and spaces
    pruned = re.sub(r"\n\s*\n+", "\n", pruned)

    # 5. Bound length
    if len(pruned) > max_chars:
        pruned = pruned[:max_chars] + "\n<!-- [PRUNED DOM TRUNCATED TO MAX LENGTH] -->"

    return pruned.strip()


def calculate_pruning_ratio(original_html: str, pruned_html: str) -> float:
    """
    Returns character reduction percentage, e.g. 0.85 means 85% reduction.
    """
    orig_len = len(original_html)
    if orig_len == 0:
        return 0.0
    pruned_len = len(pruned_html)
    return max(0.0, (orig_len - pruned_len) / orig_len)


# Backward-compatible alias for orchestrator and healing graph imports
prune_html_to_ast_skeleton = prune_dom

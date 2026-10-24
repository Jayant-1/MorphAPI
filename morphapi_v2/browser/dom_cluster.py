"""
DOM Cluster & Semantic Container Analyzer for MorphAPI V2
Discovers repeating record blocks (cards, rows, listings) and relative field selectors
while strictly ignoring navigation chrome, headers, footers, and sidebars.
"""

import logging
import re
from typing import Any
from bs4 import BeautifulSoup, Tag
from morphapi_v2.schemas.models import ContainerExtractionPlan, RelativeFieldSelector

logger = logging.getLogger("morphapi_v2.dom_cluster")

# Negative zones to strip before analyzing content
NEGATIVE_TAGS = {"nav", "header", "footer", "aside"}
NEGATIVE_CLASSES_OR_IDS = [
    "nav", "navbar", "header", "footer", "sidebar", "menu", "breadcrumb",
    "cookie", "banner", "pagination", "search-suggestions", "modal", "dialog"
]


class DomClusterAnalyzer:
    def __init__(self):
        pass

    def clean_html(self, html_content: str) -> BeautifulSoup:
        """Strips scripts, styles, and negative zones (navigation, footer, sidebar)."""
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Decompose scripts and styles
        for tag in soup.find_all(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()
            
        # Decompose negative tags
        for tag_name in NEGATIVE_TAGS:
            for el in soup.find_all(tag_name):
                el.decompose()
                
        # Decompose elements with negative class or id
        for el in soup.find_all(True):
            if el.attrs and el.name not in ("html", "body", "main"):
                cls = " ".join(el.get("class") or []).lower()
                el_id = str(el.get("id") or "").lower()
                if any(neg in cls for neg in NEGATIVE_CLASSES_OR_IDS) or any(neg in el_id for neg in NEGATIVE_CLASSES_OR_IDS):
                    el.decompose()
                    
        return soup

    def analyze_dom(
        self,
        html_content: str,
        target_schema: dict[str, str],
        target_url: str = "",
    ) -> ContainerExtractionPlan | None:
        """
        Analyzes rendered DOM to identify repeating item containers and child relative selectors.
        """
        soup = self.clean_html(html_content)
        content_root = soup.find(["main", "article"]) or soup.find(id=re.compile(r"content|app|root", re.I)) or soup.body or soup

        # -------------------------------------------------------------
        # Pattern 1: Tabular data (table > tbody > tr)
        # -------------------------------------------------------------
        tables = content_root.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            # Must have at least 2 rows (header + data or data rows)
            data_rows = [r for r in rows if r.find_all("td")]
            if len(data_rows) >= 2:
                plan = self._build_table_plan(data_rows, target_schema)
                if plan:
                    return plan

        # -------------------------------------------------------------
        # Pattern 2: Repeating Listing Anchors (e.g. YC Company Cards)
        # -------------------------------------------------------------
        # In modern directories, each card is often an <a> tag linking to /entity/<slug>
        all_anchors = content_root.find_all("a", href=True)
        # Filter for content links (links with distinct paths, avoiding root/anchor links)
        content_links = [
            a for a in all_anchors
            if a["href"] and not a["href"].startswith("#") and a["href"] not in ("/", "/about", "/contact", "/apply", "/privacy")
            and len(a.get_text(strip=True)) > 2
        ]

        if len(content_links) >= 3:
            # Check if anchors share a common class or common href prefix
            best_plan = self._build_anchor_cluster_plan(content_links, target_schema)
            if best_plan:
                return best_plan

        # -------------------------------------------------------------
        # Pattern 3: Semantic Cards (<article>, <li>, or repeating <div>)
        # -------------------------------------------------------------
        cards = content_root.find_all("article")
        if len(cards) < 2:
            cards = content_root.find_all("li")
        if len(cards) < 2:
            # Look for div clusters with common class
            cards = self._find_repeating_div_clusters(content_root)

        if len(cards) >= 2:
            plan = self._build_card_cluster_plan(cards, target_schema)
            if plan:
                return plan

        return None

    def _build_table_plan(self, data_rows: list[Tag], target_schema: dict[str, str]) -> ContainerExtractionPlan:
        sample_row = data_rows[0]
        cells = sample_row.find_all(["td", "th"])
        field_rules: dict[str, RelativeFieldSelector] = {}

        schema_keys = list(target_schema.keys())
        for idx, key in enumerate(schema_keys):
            cell_idx = idx + 1
            if cell_idx <= len(cells):
                cell = cells[cell_idx - 1]
                if cell.find("a") and any(k in key.lower() for k in ("link", "url", "href")):
                    field_rules[key] = RelativeFieldSelector(
                        selector=f"td:nth-child({cell_idx}) a",
                        attribute="href",
                    )
                else:
                    field_rules[key] = RelativeFieldSelector(
                        selector=f"td:nth-child({cell_idx})",
                        attribute="text",
                    )

        return ContainerExtractionPlan(
            strategy="hierarchical_dom",
            container_selector="table tbody tr, table tr:has(td)",
            field_rules=field_rules,
            confidence_score=0.95,
            discovery_method="table_structure",
            rationale=f"Discovered standard HTML data table with {len(data_rows)} rows",
        )

    def _build_anchor_cluster_plan(
        self,
        anchors: list[Tag],
        target_schema: dict[str, str],
    ) -> ContainerExtractionPlan | None:
        """Builds plan when repeating cards are <a> tags with rich inner content."""
        # Check if anchors have a common class
        class_counts: dict[str, int] = {}
        for a in anchors:
            classes = a.get("class") or []
            for c in classes:
                class_counts[c] = class_counts.get(c, 0) + 1

        chosen_container_selector = "a[href*='/']"
        # If a class appears on >= 60% of content anchors, use it
        for c, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= len(anchors) * 0.5 and count >= 3:
                chosen_container_selector = f"a.{c}"
                break

        # If no specific class, check common href path prefix (e.g. /companies/)
        if chosen_container_selector == "a[href*='/']":
            href_samples = [a["href"] for a in anchors[:10]]
            # Find common subpath
            subpath_match = re.search(r"(/[\w-]+/)", href_samples[0])
            if subpath_match:
                prefix = subpath_match.group(1)
                matching = [h for h in href_samples if prefix in h]
                if len(matching) >= len(href_samples) * 0.5:
                    chosen_container_selector = f"a[href*='{prefix}']"

        # Now derive relative child selectors inside sample anchor
        sample_a = anchors[0]
        field_rules: dict[str, RelativeFieldSelector] = {}

        for field_name in target_schema.keys():
            norm_name = field_name.lower().replace("_", "")
            
            # 1. Link / URL field
            if any(k in norm_name for k in ("link", "url", "href", "website")):
                # The container itself is an anchor!
                field_rules[field_name] = RelativeFieldSelector(
                    selector=".",
                    attribute="href",
                    fallback_selectors=["a"],
                )
            # 2. Name / Title / Company field
            elif any(k in norm_name for k in ("name", "title", "company", "header", "heading")):
                # Look for h1-h5, strong, b, or class containing name/title
                title_tag = (
                    sample_a.find(class_=re.compile(r"coName|name|title|heading", re.I))
                    or sample_a.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
                    or sample_a.find("span")
                )
                if title_tag and title_tag.get("class"):
                    cls_name = title_tag["class"][0]
                    field_rules[field_name] = RelativeFieldSelector(
                        selector=f"{title_tag.name}.{cls_name}",
                        attribute="text",
                        fallback_selectors=[title_tag.name, "h3", "strong", "."],
                    )
                elif title_tag:
                    field_rules[field_name] = RelativeFieldSelector(
                        selector=title_tag.name,
                        attribute="text",
                        fallback_selectors=["h3", "strong", "span"],
                    )
                else:
                    field_rules[field_name] = RelativeFieldSelector(selector=".", attribute="text")
            # 3. Description / Summary field
            elif any(k in norm_name for k in ("desc", "detail", "summary", "oneliner", "text")):
                desc_tag = (
                    sample_a.find(class_=re.compile(r"desc|detail|summary|oneliner", re.I))
                    or sample_a.find("p")
                    or sample_a.find_all("span")[-1] if len(sample_a.find_all("span")) > 1 else None
                )
                if desc_tag and desc_tag.get("class"):
                    cls_name = desc_tag["class"][0]
                    field_rules[field_name] = RelativeFieldSelector(
                        selector=f"{desc_tag.name}.{cls_name}",
                        attribute="text",
                        fallback_selectors=[desc_tag.name, "p", "span"],
                    )
                elif desc_tag:
                    field_rules[field_name] = RelativeFieldSelector(
                        selector=desc_tag.name,
                        attribute="text",
                        fallback_selectors=["p", "span"],
                    )
                else:
                    field_rules[field_name] = RelativeFieldSelector(selector="p, span", attribute="text")
            else:
                field_rules[field_name] = RelativeFieldSelector(selector="*", attribute="text")

        return ContainerExtractionPlan(
            strategy="hierarchical_dom",
            container_selector=chosen_container_selector,
            field_rules=field_rules,
            confidence_score=0.92,
            discovery_method="anchor_card_cluster",
            rationale=f"Identified repeating card collection with {len(anchors)} items matching selector '{chosen_container_selector}'",
        )

    def _find_repeating_div_clusters(self, content_root: Tag) -> list[Tag]:
        """Finds repeating div containers that share the same class and have child text."""
        divs = content_root.find_all("div", class_=True)
        class_groups: dict[str, list[Tag]] = {}
        for d in divs:
            # Combine classes
            key = ".".join(sorted(d.get("class") or []))
            if key and len(d.get_text(strip=True)) > 10:
                class_groups.setdefault(key, []).append(d)

        # Return the largest group with >= 2 items
        sorted_groups = sorted(class_groups.values(), key=len, reverse=True)
        if sorted_groups and len(sorted_groups[0]) >= 2:
            return sorted_groups[0]
        return []

    def _build_card_cluster_plan(
        self,
        cards: list[Tag],
        target_schema: dict[str, str],
    ) -> ContainerExtractionPlan | None:
        sample_card = cards[0]
        container_tag = sample_card.name
        classes = sample_card.get("class") or []
        container_selector = f"{container_tag}.{classes[0]}" if classes else container_tag

        field_rules: dict[str, RelativeFieldSelector] = {}
        for field_name in target_schema.keys():
            norm = field_name.lower().replace("_", "")
            if any(k in norm for k in ("link", "url", "href")):
                a = sample_card.find("a")
                field_rules[field_name] = RelativeFieldSelector(
                    selector="a" if a else ".",
                    attribute="href",
                )
            elif any(k in norm for k in ("name", "title", "company", "header")):
                h = sample_card.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"]) or sample_card.find("a")
                field_rules[field_name] = RelativeFieldSelector(
                    selector=h.name if h else "h3, strong, a",
                    attribute="text",
                )
            elif any(k in norm for k in ("desc", "detail", "summary", "text")):
                p = sample_card.find(["p", "span"])
                field_rules[field_name] = RelativeFieldSelector(
                    selector=p.name if p else "p",
                    attribute="text",
                )
            else:
                field_rules[field_name] = RelativeFieldSelector(selector="*", attribute="text")

        return ContainerExtractionPlan(
            strategy="hierarchical_dom",
            container_selector=container_selector,
            field_rules=field_rules,
            confidence_score=0.88,
            discovery_method="card_cluster",
            rationale=f"Identified repeating card structure using container '{container_selector}'",
        )


dom_cluster_analyzer = DomClusterAnalyzer()

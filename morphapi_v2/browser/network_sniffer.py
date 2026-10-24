"""
Network Response Sniffer for MorphAPI V2
Passively intercepts JSON responses from internal APIs (Algolia, REST, GraphQL) during page load.
"""

import json
import logging
from typing import Any
from playwright.async_api import Page, Response

logger = logging.getLogger("morphapi_v2.sniffer")


class NetworkSniffer:
    def __init__(self, target_fields: list[str] | None = None):
        self.target_fields = [f.lower().replace("_", "") for f in (target_fields or [])]
        self.captured_payloads: list[dict[str, Any]] = []

    def attach(self, page: Page):
        """Attaches response listener to page."""
        page.on("response", self._handle_response)

    async def _handle_response(self, response: Response):
        try:
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" not in content_type and "text/json" not in content_type and "+json" not in content_type:
                return

            # Avoid huge binary files or telemetry
            url = response.url.lower()
            if any(skip in url for skip in ["sentry", "google-analytics", "doubleclick", "posthog", "telemetry", "hotjar"]):
                return

            text = await response.text()
            if not text or len(text) < 50 or len(text) > 10_000_000:
                return

            data = json.loads(text)
            self._search_arrays(data, url)
        except Exception:
            pass

    def _search_arrays(self, data: Any, url: str, path: str = "root"):
        if isinstance(data, list):
            if len(data) >= 3 and all(isinstance(item, dict) for item in data[:5]):
                score, mapping = self._evaluate_record_match(data[:5])
                if score > 0.4:
                    logger.info("[NetworkSniffer] Intercepted strong JSON dataset match at '%s' (score: %.2f)", url, score)
                    self.captured_payloads.append({
                        "url": url,
                        "path": path,
                        "records": data,
                        "score": score,
                        "field_mapping": mapping,
                    })
            for idx, item in enumerate(data[:3]):
                self._search_arrays(item, url, f"{path}[{idx}]")
        elif isinstance(data, dict):
            # Special check for Algolia 'results' -> 'hits'
            if "results" in data and isinstance(data["results"], list):
                for r_idx, res in enumerate(data["results"]):
                    if isinstance(res, dict) and "hits" in res and isinstance(res["hits"], list):
                        hits = res["hits"]
                        if len(hits) >= 3:
                            score, mapping = self._evaluate_record_match(hits[:5])
                            if score > 0.4:
                                logger.info("[NetworkSniffer] Intercepted Algolia hits array at '%s' (score: %.2f)", url, score)
                                self.captured_payloads.append({
                                    "url": url,
                                    "path": f"results[{r_idx}].hits",
                                    "records": hits,
                                    "score": score,
                                    "field_mapping": mapping,
                                })
            for k, v in data.items():
                if isinstance(v, (list, dict)):
                    self._search_arrays(v, url, f"{path}.{k}")

    def _evaluate_record_match(self, sample_records: list[dict[str, Any]]) -> tuple[float, dict[str, str]]:
        """Computes overlap score between target fields and record keys."""
        if not sample_records or not self.target_fields:
            return 0.0, {}

        # Collect all keys from sample records
        sample_keys = set()
        for rec in sample_records:
            sample_keys.update([k.lower().replace("_", "") for k in rec.keys()])

        matched_mapping: dict[str, str] = {}
        for target in self.target_fields:
            # Direct match
            for rec_k in sample_records[0].keys():
                norm_k = rec_k.lower().replace("_", "")
                if target in norm_k or norm_k in target:
                    matched_mapping[target] = rec_k
                    break
                # Common synonyms: link -> website / url / href
                if target in ("link", "url") and norm_k in ("website", "url", "href", "link", "domain"):
                    matched_mapping[target] = rec_k
                    break
                if target in ("name", "title", "company") and norm_k in ("name", "title", "companyname", "slug"):
                    matched_mapping[target] = rec_k
                    break
                if target in ("description", "detail") and norm_k in ("oneliner", "description", "longdescription", "summary", "detail"):
                    matched_mapping[target] = rec_k
                    break

        score = len(matched_mapping) / max(len(self.target_fields), 1)
        return score, matched_mapping

    def get_best_match(self) -> dict[str, Any] | None:
        if not self.captured_payloads:
            return None
        # Sort by score descending
        sorted_payloads = sorted(self.captured_payloads, key=lambda x: x["score"], reverse=True)
        return sorted_payloads[0]

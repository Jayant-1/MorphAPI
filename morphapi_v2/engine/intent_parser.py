"""
Intent Parser for MorphAPI V2
Extracts API metadata, input parameters, and output schema directly from user intent and target URL.
"""

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from morphapi_v2.schemas.intent import ParsedIntent, ParameterDefinition, FieldDefinition


class IntentParserV2:
    def __init__(self):
        pass

    def parse(
        self,
        prompt: str,
        target_url: str | None = None,
        name: str | None = None,
    ) -> ParsedIntent:
        # 1. Resolve Target URL
        resolved_url = target_url or ""
        if not resolved_url or not resolved_url.startswith("http"):
            url_match = re.search(r"https?://[^\s\"'<>]+", prompt)
            if url_match:
                resolved_url = url_match.group(0).rstrip(".,;")
            else:
                resolved_url = "https://example.com"

        # 2. Extract Parameter Placeholders (e.g. {batch}, {year}, {query})
        param_names = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", resolved_url))
        
        # Check if prompt mentions configurable parameters
        config_matches = re.findall(r"configurable\s+([a-zA-Z0-9_]+(?:\s+or\s+[a-zA-Z0-9_]+)*)", prompt, re.I)
        for cm in config_matches:
            for p in re.split(r"\s+or\s+|\s+and\s+|,", cm):
                p_clean = p.strip().lower()
                if p_clean and len(p_clean) < 20:
                    param_names.add(p_clean)

        inputs: dict[str, ParameterDefinition] = {}
        for p in param_names:
            is_path = f"{{{p}}}" in urlparse(resolved_url).path
            inputs[p] = ParameterDefinition(
                name=p,
                type="str",
                description=f"Filter by {p}",
                default_value="",
                is_path_param=is_path,
                is_query_param=not is_path,
            )

        # 3. Create Sample Inspection URL for testing
        # When URL has template query parameters (e.g. ?batch={batch}), strip template filters to inspect base listing
        parsed = urlparse(resolved_url)
        clean_inspection_url = resolved_url
        if "{" in parsed.query:
            qs = parse_qs(parsed.query)
            clean_qs = {k: [v for v in vals if "{" not in v] for k, vals in qs.items()}
            clean_qs = {k: v for k, v in clean_qs.items() if v}
            new_q = urlencode(clean_qs, doseq=True)
            clean_inspection_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))
        elif "{" in parsed.path:
            clean_inspection_url = re.sub(r"\{[a-zA-Z0-9_]+\}", "", resolved_url).rstrip("/")

        # 4. Extract Output Schema Fields from Prompt
        schema_def: dict[str, str] = {}
        field_defs: list[FieldDefinition] = []

        # Check for explicit extract directives: e.g. "Extract company name, description, and link."
        extract_match = re.search(r"extract\s+([^.\n]+)", prompt, re.I)
        extracted_phrases = []
        if extract_match:
            raw_fields = extract_match.group(1)
            # Split by comma, 'and', 'or'
            parts = re.split(r",|\sand\s|\sor\s", raw_fields)
            for part in parts:
                cleaned = re.sub(r"[^a-zA-Z0-9_ ]", "", part).strip().lower()
                if cleaned and cleaned not in ("etc", "all", "the"):
                    extracted_phrases.append(cleaned)

        if extracted_phrases:
            for phrase in extracted_phrases:
                field_slug = re.sub(r"\s+", "_", phrase)
                # Map field type
                ftype = "str"
                if any(k in field_slug for k in ("price", "cost", "amount", "salary")):
                    ftype = "float"
                elif any(k in field_slug for k in ("count", "number", "id", "year", "rank")):
                    ftype = "int"
                elif any(k in field_slug for k in ("is_", "has_", "available")):
                    ftype = "bool"

                schema_def[field_slug] = ftype
                field_defs.append(FieldDefinition(name=field_slug, type=ftype, description=phrase.title()))
        else:
            # Fallback default fields if prompt didn't specify
            schema_def = {"title": "str", "description": "str", "link": "str"}
            field_defs = [
                FieldDefinition(name="title", type="str", description="Title or Name"),
                FieldDefinition(name="description", type="str", description="Summary or Detail"),
                FieldDefinition(name="link", type="str", description="Destination Link"),
            ]

        # 5. Derive Slug and Name
        if not name:
            path_parts = [p for p in parsed.path.split("/") if p]
            domain = parsed.netloc.replace("www.", "").split(".")[0]
            if path_parts:
                slug = f"{domain}-{path_parts[0]}"[:35].lower()
                display_name = f"{domain.title()} {path_parts[0].title()} API"
            else:
                slug = f"{domain}-api"[:35].lower()
                display_name = f"{domain.title()} API"
        else:
            slug = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower()).strip("-")[:40]
            display_name = name

        entity_name = "item"
        for candidate_entity in ("company", "startup", "product", "article", "job", "post", "user", "book"):
            if candidate_entity in prompt.lower() or candidate_entity in slug.lower():
                entity_name = candidate_entity
                break

        return ParsedIntent(
            name=display_name,
            slug=slug,
            entity_name=entity_name,
            target_url_template=resolved_url,
            sample_inspection_url=clean_inspection_url,
            inputs=inputs,
            schema_definition=schema_def,
            field_definitions=field_defs,
            raw_prompt=prompt,
            rationale=f"Synthesized API for '{entity_name}' with {len(schema_def)} fields and {len(inputs)} parameters",
        )


intent_parser_v2 = IntentParserV2()

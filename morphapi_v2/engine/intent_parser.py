"""
Intent Parser for MorphAPI V2
Extracts API metadata, input parameters, and output schema directly from user intent and target URL.
"""

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from morphapi_v2.schemas.intent import ParsedIntent, ParameterDefinition, FieldDefinition
from morphapi_v2.schemas.models import EndpointContract, ParameterSpec, FieldTypeSpec


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
        
        # Check if prompt mentions configurable parameters (e.g. "configurable batch or year", "configurable min_score and limit", "specify latitude, longitude")
        config_matches = re.findall(r"(?:configurable|specify|configure|filter by)\s+([a-zA-Z0-9_ ]+?)(?:\s+to\s+return|\.|\n|$)", prompt, re.I)
        for cm in config_matches:
            for p in re.split(r",|\sand\s|\sor\s", cm):
                p_clean = re.sub(r"^(?:the|a)\s+", "", p.strip().lower())
                p_clean = re.sub(r"\s+of\s+", "_", p_clean)
                p_clean = re.sub(r"\s+", "_", p_clean)
                p_clean = re.sub(r"[^a-zA-Z0-9_]", "", p_clean)
                if p_clean and len(p_clean) < 30 and p_clean not in ("a", "the", "an", "for"):
                    param_names.add(p_clean)

        inputs: dict[str, ParameterDefinition] = {}
        param_specs: list[ParameterSpec] = []
        for p in param_names:
            is_path = f"{{{p}}}" in urlparse(resolved_url).path
            ptype = "str"
            default_val: Any = ""
            if any(k in p for k in ("latitude", "lat", "longitude", "lon")):
                ptype = "float"
                default_val = 52.52 if "lat" in p else 13.41
            elif any(k in p for k in ("limit", "count", "page", "min_score", "score", "record")):
                ptype = "int"
                default_val = 7 if "record" in p else (30 if "limit" in p else (1 if "page" in p else 0))
            elif any(k in p for k in ("price", "min_price", "max_price")):
                ptype = "float"
                default_val = 0.0

            inputs[p] = ParameterDefinition(
                name=p,
                type=ptype,
                description=f"Filter by {p}",
                default_value=default_val,
                is_path_param=is_path,
                is_query_param=not is_path,
            )
            param_specs.append(ParameterSpec(
                name=p,
                type=ptype,
                location="path" if is_path else "query",
                default=default_val,
                required=is_path,
                description=f"Filter or parameter: {p}",
            ))

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
        field_specs: list[FieldTypeSpec] = []

        # Check for explicit extract directives: e.g. "Extract company name, description, and link."
        extract_match = re.search(r"extract\s+([^.\n]+)", prompt, re.I)
        extracted_phrases = []
        if extract_match:
            raw_fields = extract_match.group(1)
            # Split by comma, 'and', 'or'
            parts = re.split(r",|\sand\s|\sor\s", raw_fields)
            for part in parts:
                cleaned = part.strip().lower()
                cleaned = re.sub(r"\s+for\s+.*$", "", cleaned)
                cleaned = re.sub(r"^(?:the|a)\s+", "", cleaned)
                cleaned = re.sub(r"[^a-zA-Z0-9_ ]", "", cleaned).strip()
                if cleaned and cleaned not in ("etc", "all", "the"):
                    extracted_phrases.append(cleaned)

        if extracted_phrases:
            for phrase in extracted_phrases:
                field_slug = re.sub(r"\s+", "_", phrase)
                # Map field type
                ftype = "str"
                target_type = "str"
                if any(k in field_slug for k in ("price", "cost", "amount", "salary", "rating", "stars", "percent")):
                    ftype = "float"
                    target_type = "float"
                elif any(k in field_slug for k in ("score", "points", "count", "number", "id", "year", "rank", "votes")):
                    ftype = "int"
                    target_type = "int"
                elif any(k in field_slug for k in ("is_", "has_", "available", "active", "verified")):
                    ftype = "bool"
                    target_type = "bool"
                elif any(k in field_slug for k in ("link", "url", "href", "website")):
                    ftype = "str"
                    target_type = "url"
                elif any(k in field_slug for k in ("tags", "categories", "skills", "topics")):
                    ftype = "list"
                    target_type = "list[str]"

                schema_def[field_slug] = ftype
                field_defs.append(FieldDefinition(name=field_slug, type=ftype, description=phrase.title()))
                field_specs.append(FieldTypeSpec(name=field_slug, target_type=target_type, description=phrase.title()))
        else:
            # Fallback default fields if prompt didn't specify
            schema_def = {"title": "str", "description": "str", "link": "str"}
            field_defs = [
                FieldDefinition(name="title", type="str", description="Title or Name"),
                FieldDefinition(name="description", type="str", description="Summary or Detail"),
                FieldDefinition(name="link", type="str", description="Destination Link"),
            ]
            field_specs = [
                FieldTypeSpec(name="title", target_type="str", description="Title or Name"),
                FieldTypeSpec(name="description", target_type="str", description="Summary or Detail"),
                FieldTypeSpec(name="link", target_type="url", description="Destination Link"),
            ]

        # Infer Response Shape from Prompt
        response_shape = "list"
        if re.search(r"\b(single|detail|profile|summary|individual|single item|single entity)\b", prompt, re.I):
            response_shape = "single_object"
        elif re.search(r"\b(paginated|pagination|page and limit)\b", prompt, re.I):
            response_shape = "paginated"

        contract = EndpointContract(
            response_shape=response_shape,
            parameters=param_specs,
            fields=field_specs,
            http_methods=["GET", "POST"],
        )

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
            response_shape=response_shape,
            contract=contract,
            raw_prompt=prompt,
            rationale=f"Synthesized API for '{entity_name}' with {len(schema_def)} fields and {len(inputs)} parameters",
        )


intent_parser_v2 = IntentParserV2()

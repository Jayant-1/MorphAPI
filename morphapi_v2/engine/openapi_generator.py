"""
Dynamic OpenAPI 3.1 Specification and Documentation Generator for MorphAPI V2
Generates dedicated OpenAPI contracts and interactive Swagger UI per synthesized endpoint.
"""

from typing import Any


class OpenApiGeneratorV2:
    @staticmethod
    def type_to_openapi_type(t: str) -> tuple[str, str | None]:
        t_low = t.lower().strip()
        if t_low in ("int", "integer"):
            return "integer", "int64"
        if t_low in ("float", "number"):
            return "number", "float"
        if t_low in ("bool", "boolean"):
            return "boolean", None
        if t_low in ("url", "uri"):
            return "string", "uri"
        if t_low in ("list[str]", "list", "array"):
            return "array", None
        return "string", None

    @classmethod
    def generate_spec(
        cls,
        endpoint_dict: dict[str, Any],
        base_server_url: str = "http://localhost:8001",
    ) -> dict[str, Any]:
        api_name = endpoint_dict.get("api_name", "Dynamic API")
        user_id = endpoint_dict.get("user_id", "default")
        slug = endpoint_dict.get("slug", "endpoint")
        target_url = endpoint_dict.get("target_url", "")
        schema_def = endpoint_dict.get("schema_definition", {})
        inputs = endpoint_dict.get("inputs", {})
        plan = endpoint_dict.get("plan", {})
        contract = plan.get("contract") or {}

        response_shape = contract.get("response_shape", "list")
        param_specs = contract.get("parameters") or []
        http_methods = contract.get("http_methods") or ["GET", "POST"]

        # Build OpenAPI Parameters
        parameters: list[dict[str, Any]] = []

        # From contract parameter specs or inputs
        if param_specs:
            for p in param_specs:
                ptype, pfmt = cls.type_to_openapi_type(p.get("type", "str"))
                schema_obj: dict[str, Any] = {"type": ptype}
                if pfmt:
                    schema_obj["format"] = pfmt
                if p.get("default") is not None:
                    schema_obj["default"] = p["default"]
                if p.get("enum_values"):
                    schema_obj["enum"] = p["enum_values"]

                parameters.append({
                    "name": p.get("name"),
                    "in": p.get("location", "query"),
                    "required": p.get("required", False),
                    "description": p.get("description", f"Filter or input for {p.get('name')}"),
                    "schema": schema_obj,
                })
        elif inputs:
            for pname, pdef in inputs.items():
                p_type_str = pdef.get("type", "str") if isinstance(pdef, dict) else "str"
                ptype, pfmt = cls.type_to_openapi_type(p_type_str)
                schema_obj = {"type": ptype}
                if pfmt:
                    schema_obj["format"] = pfmt
                parameters.append({
                    "name": pname,
                    "in": "query",
                    "required": False,
                    "description": f"Configurable parameter: {pname}",
                    "schema": schema_obj,
                })

        # Build Response Properties Schema
        record_properties: dict[str, Any] = {}
        for fname, ftype in schema_def.items():
            ftype_str = ftype if isinstance(ftype, str) else ftype.get("target_type", "str")
            open_type, open_fmt = cls.type_to_openapi_type(ftype_str)
            prop: dict[str, Any] = {"type": open_type}
            if open_fmt:
                prop["format"] = open_fmt
            if open_type == "array":
                prop["items"] = {"type": "string"}
            record_properties[fname] = prop

        record_schema = {
            "type": "object",
            "properties": record_properties,
        }

        if response_shape == "single_object":
            response_schema = record_schema
        elif response_shape == "paginated":
            response_schema = {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "example": 1},
                    "limit": {"type": "integer", "example": 20},
                    "count": {"type": "integer", "example": 20},
                    "total": {"type": "integer", "example": 100},
                    "has_more": {"type": "boolean", "example": True},
                    "data": {
                        "type": "array",
                        "items": record_schema,
                    },
                },
            }
        else:  # "list"
            response_schema = {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string", "example": f"/v2/api/{user_id}/{slug}"},
                    "count": {"type": "integer", "example": 25},
                    "data": {
                        "type": "array",
                        "items": record_schema,
                    },
                },
            }

        endpoint_path = f"/v2/api/{user_id}/{slug}"

        get_operation = {
            "summary": f"Query {api_name}",
            "description": f"Live data extraction endpoint for '{target_url}' synthesized by MorphAPI V2.",
            "operationId": f"query_{slug}",
            "parameters": parameters,
            "responses": {
                "200": {
                    "description": "Successful extraction result",
                    "content": {
                        "application/json": {
                            "schema": response_schema,
                        },
                    },
                },
                "404": {"description": "Endpoint not found"},
                "500": {"description": "Live extraction runtime error"},
            },
        }

        paths_obj: dict[str, Any] = {
            endpoint_path: {
                "get": get_operation,
            }
        }

        # Add POST operation if supported
        if "POST" in [m.upper() for m in http_methods]:
            post_operation = {
                "summary": f"Filter/Query {api_name} via POST payload",
                "description": f"Accepts JSON query filters to parameterize extraction for '{target_url}'.",
                "operationId": f"query_post_{slug}",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    p["name"]: p["schema"] for p in parameters
                                },
                            },
                        },
                    },
                },
                "responses": get_operation["responses"],
            }
            paths_obj[endpoint_path]["post"] = post_operation

        spec = {
            "openapi": "3.1.0",
            "info": {
                "title": f"MorphAPI - {api_name}",
                "version": "1.0.0",
                "description": f"Automated REST API synthesized for `{target_url}`.\nShape: `{response_shape}`.",
            },
            "servers": [
                {"url": base_server_url, "description": "MorphAPI V2 Server"},
            ],
            "paths": paths_obj,
        }
        return spec

    @staticmethod
    def generate_swagger_ui_html(openapi_json_url: str, title: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title} - Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" >
    <style>
        html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
        *, *:before, *:after {{ box-sizing: inherit; }}
        body {{ margin: 0; background: #fafafa; font-family: sans-serif; }}
        .topbar {{ display: none !important; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
    window.onload = function() {{
        SwaggerUIBundle({{
            url: "{openapi_json_url}",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            layout: "BaseLayout"
        }});
    }};
    </script>
</body>
</html>"""


openapi_generator_v2 = OpenApiGeneratorV2()

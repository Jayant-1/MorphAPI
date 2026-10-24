"""
Extraction Plan & Runtime Models for MorphAPI V2
"""

from typing import Any
from pydantic import BaseModel, Field, model_validator


class ParameterSpec(BaseModel):
    name: str
    type: str = "str"  # "str", "int", "float", "bool"
    location: str = "query"  # "query", "path", "body"
    default: Any = None
    required: bool = False
    description: str = ""
    enum_values: list[str] | None = None


class FieldTypeSpec(BaseModel):
    name: str
    target_type: str = "str"  # "str", "int", "float", "bool", "url", "list[str]"
    clean_regex: str | None = None
    default: Any = None
    description: str = ""


class EndpointContract(BaseModel):
    response_shape: str = "list"  # "list", "single_object", "paginated"
    parameters: list[ParameterSpec] = Field(default_factory=list)
    fields: list[FieldTypeSpec] = Field(default_factory=list)
    http_methods: list[str] = Field(default_factory=lambda: ["GET", "POST"])


class RelativeFieldSelector(BaseModel):
    selector: str
    attribute: str = "text"  # "text", "href", "src", "title", "value"
    fallback_selectors: list[str] = Field(default_factory=list)
    clean_regex: str | None = None


class ContainerExtractionPlan(BaseModel):
    strategy: str = "hierarchical_dom"  # "hierarchical_dom", "intercepted_api", or "custom_js"
    container_selector: str = ""
    field_rules: dict[str, RelativeFieldSelector] = Field(default_factory=dict)
    
    # Custom Playwright browser execution script
    custom_js_extractor: str | None = None

    # Optional dynamic contract
    contract: EndpointContract | None = None

    # Optional API sniffing route
    intercepted_api_url_pattern: str | None = None
    intercepted_hits_path: str | None = None
    intercepted_field_map: dict[str, str] = Field(default_factory=dict)
    
    confidence_score: float = 1.0
    discovery_method: str = "dom_clustering"
    rationale: str = ""


class ExtractionResult(BaseModel):
    success: bool
    data: list[dict[str, Any]] | dict[str, Any] | None = None
    count: int = 0
    latency_ms: int = 0
    strategy_used: str = "hierarchical_dom"
    error_message: str | None = None
    validation_issues: list[str] = Field(default_factory=list)


class EndpointV2CreateRequest(BaseModel):
    prompt: str = Field(default="", description="Natural language intent or extraction prompt")
    target_url: str | None = None
    url: str | None = None  # Common alias for target_url
    name: str | None = None
    user_id: str = "default"

    @model_validator(mode="before")
    @classmethod
    def populate_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If 'url' is provided instead of 'target_url'
            if "url" in data and not data.get("target_url"):
                data["target_url"] = data["url"]
            # If 'prompt' is empty but target_url is provided
            if not data.get("prompt") and data.get("target_url"):
                data["prompt"] = f"Create an API extracting title, description, and link from {data['target_url']}"
        return data


class EndpointV2Response(BaseModel):
    endpoint_id: str
    user_id: str
    api_name: str
    slug: str
    name: str
    status: str = "ACTIVE"
    target_url: str
    api_key: str
    endpoint_url: str
    full_endpoint_url: str
    openapi_url: str | None = None
    docs_url: str | None = None
    curl_command: str
    api_specification: dict[str, Any]
    contract: EndpointContract | None = None
    schema_definition: dict[str, str]
    sample_data: list[dict[str, Any]]
    message: str

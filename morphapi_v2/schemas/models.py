"""
Extraction Plan & Runtime Models for MorphAPI V2
"""

from typing import Any
from pydantic import BaseModel, Field


class RelativeFieldSelector(BaseModel):
    selector: str
    attribute: str = "text"  # "text", "href", "src", "title", "value"
    fallback_selectors: list[str] = Field(default_factory=list)
    clean_regex: str | None = None


class ContainerExtractionPlan(BaseModel):
    strategy: str = "hierarchical_dom"  # "hierarchical_dom" or "intercepted_api"
    container_selector: str = ""
    field_rules: dict[str, RelativeFieldSelector] = Field(default_factory=dict)
    
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
    prompt: str
    target_url: str | None = None
    name: str | None = None
    user_id: str = "default"


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
    curl_command: str
    api_specification: dict[str, Any]
    schema_definition: dict[str, str]
    sample_data: list[dict[str, Any]]
    message: str

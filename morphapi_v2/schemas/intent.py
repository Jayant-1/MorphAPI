"""
User Prompt & Intent Models for MorphAPI V2
"""

from typing import Any
from pydantic import BaseModel, Field


class ParameterDefinition(BaseModel):
    name: str
    type: str = "str"
    description: str = ""
    default_value: Any = ""
    is_path_param: bool = False
    is_query_param: bool = True


class FieldDefinition(BaseModel):
    name: str
    type: str = "str"  # "str", "int", "float", "bool", "url", "list"
    description: str = ""
    required: bool = True
    aliases: list[str] = Field(default_factory=list)


class ParsedIntent(BaseModel):
    name: str
    slug: str
    entity_name: str
    target_url_template: str
    sample_inspection_url: str
    inputs: dict[str, ParameterDefinition] = Field(default_factory=dict)
    schema_definition: dict[str, str] = Field(default_factory=dict)
    field_definitions: list[FieldDefinition] = Field(default_factory=list)
    raw_prompt: str = ""
    rationale: str = ""

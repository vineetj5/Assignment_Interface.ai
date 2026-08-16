"""Data models for Phase 4 Capability Artifact Schema."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


# --- Status and Enums ---

class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class ArtifactActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    EXTRACT = "extract"
    WAIT = "wait"


class InputType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"


class OutputType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    MONEY = "money"
    OBJECT = "object"


class OutcomeCategory(str, Enum):
    BUSINESS_OUTCOME = "business_outcome"
    HARD_FAILURE = "hard_failure"
    RECOVERABLE = "recoverable"
    ESCALATE = "escalate"


# --- Identity ---

class CapabilityIdentity(BaseModel):
    name: str = Field(..., description="Canonical name of the capability, e.g. lookup_balance")
    version: str = Field(..., description="Semantic version of the capability, e.g. 1.0.0")
    description: str = Field(..., description="Human-readable description of what this capability achieves")
    status: ArtifactStatus = Field(default=ArtifactStatus.DRAFT, description="Lifecycle status")


# --- Input Contract ---

class InputValidationSpec(BaseModel):
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None


class InputSpec(BaseModel):
    name: str
    type: InputType
    required: bool = True
    description: Optional[str] = None
    values: Optional[List[str]] = Field(default=None, description="Allowed values if type is enum")
    validation: Optional[InputValidationSpec] = None
    sensitive: bool = False


# --- Output Contract ---

class OutputSchemaSpec(BaseModel):
    amount: Optional[Dict[str, str]] = None
    currency: Optional[Dict[str, str]] = None


class OutputSpec(BaseModel):
    name: str
    type: OutputType
    description: Optional[str] = None
    values: Optional[List[str]] = None
    schema_def: Optional[Dict[str, Any]] = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


# --- Value Sources & References ---

class ValueSource(BaseModel):
    source: Literal["input", "input_map", "literal", "env", "previous_step"]
    name: Optional[str] = None
    input: Optional[str] = None
    mapping: Optional[Dict[str, str]] = None
    value: Optional[Any] = None
    step_id: Optional[str] = None


# --- Target Locators & Frames ---

class FrameTarget(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None


class LocatorStrategy(BaseModel):
    strategy: str = Field(
        ...,
        description="Strategy type: role_name, label, field_by_label, table_row_action, attributes, text, css",
    )
    role: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    tag: Optional[str] = None
    type: Optional[str] = None
    value: Optional[Union[str, ValueSource]] = None
    table: Optional[str] = None
    row_match: Optional[Dict[str, Any]] = None
    action_control: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, str]] = None
    css: Optional[str] = None


class TargetSpec(BaseModel):
    frame_path: List[FrameTarget] = Field(default_factory=list)
    primary: LocatorStrategy
    fallbacks: List[LocatorStrategy] = Field(default_factory=list)


# --- Conditions, Waits & Checks ---

class WaitSpec(BaseModel):
    type: str = Field(..., description="Condition type: text_visible, any_of, networkidle, domcontentloaded, sleep")
    value: Optional[Union[str, int]] = None
    conditions: Optional[List[WaitSpec]] = None
    timeout_ms: int = Field(default=5000)


class ConditionSpec(BaseModel):
    type: str = Field(
        ...,
        description="input_value_equals, text_matches, text_visible, field_equals, member_matches_input, account_matches_input, output_present, all_of, any_of",
    )
    expected: Optional[Union[str, ValueSource]] = None
    field: Optional[Dict[str, Any]] = None
    input: Optional[str] = None
    output: Optional[str] = None
    pattern: Optional[str] = None
    table: Optional[str] = None
    column: Optional[str] = None
    conditions: Optional[List[ConditionSpec]] = None


# --- Extractions ---

class ExtractionTransformSpec(BaseModel):
    type: str = Field(default="parse_currency", description="Transform type: parse_currency, regex, trim, to_lower")
    default_currency: Optional[str] = "USD"
    regex_pattern: Optional[str] = None


class ExtractionSpec(BaseModel):
    output: str = Field(..., description="Output variable name defined in OutputSpec")
    attribute: Optional[str] = None
    transform: Optional[ExtractionTransformSpec] = None


# --- Steps ---

class ConditionHandler(BaseModel):
    detect: ConditionSpec
    outcome_code: str
    action: Optional[str] = None


class CapabilityStep(BaseModel):
    id: str
    action: ArtifactActionType
    target: Optional[TargetSpec] = None
    value: Optional[ValueSource] = None
    wait_before: Optional[WaitSpec] = None
    wait_after: Optional[WaitSpec] = None
    postconditions: List[ConditionSpec] = Field(default_factory=list)
    extraction: Optional[ExtractionSpec] = None
    on_conditions: List[ConditionHandler] = Field(default_factory=list)


# --- Outcomes & Runtime Conditions ---

class OutcomeSpec(BaseModel):
    code: str
    category: OutcomeCategory = OutcomeCategory.BUSINESS_OUTCOME
    detect: ConditionSpec
    description: Optional[str] = None


class RecoverySpec(BaseModel):
    action: str
    timeout_ms: int = 5000
    max_attempts: int = 1


class RuntimeConditionSpec(BaseModel):
    code: str
    category: OutcomeCategory
    detect: ConditionSpec
    recovery: Optional[RecoverySpec] = None
    description: Optional[str] = None


# --- Entrypoint, Safety, Compatibility, Provenance ---

class EntryPointSpec(BaseModel):
    url: str
    initial_wait: Optional[WaitSpec] = None


class SafetySpec(BaseModel):
    risk_class: str = Field(default="read_only", description="e.g. read_only, state_modifying, financial_transaction")
    allowed_actions: List[str] = Field(default_factory=lambda: ["fill", "click", "extract", "wait", "navigate"])
    allowed_origins: List[str] = Field(default_factory=lambda: ["http://127.0.0.1:8000"])
    contains_sensitive_inputs: bool = True
    persist_input_values: bool = False


class CompatibilitySpec(BaseModel):
    surface_type: str = "web"
    surface_adapter: str = "playwright"
    application_family: str = "cucore_mock"
    tested_versions: List[str] = Field(default_factory=lambda: ["8.4.12"])


class ProvenanceSpec(BaseModel):
    created_from: str = "llm_discovery"
    discovery_run_id: str
    created_at: str
    model_provider: Optional[str] = "groq"
    model: Optional[str] = "llama-3.3-70b-versatile"


# --- Root Capability Artifact ---

class CapabilityArtifact(BaseModel):
    schema_version: str = Field(default="1", description="Artifact schema file-format version")
    identity: CapabilityIdentity
    inputs: List[InputSpec]
    outputs: List[OutputSpec]
    entrypoint: EntryPointSpec
    steps: List[CapabilityStep]
    success_condition: ConditionSpec
    business_outcomes: List[OutcomeSpec] = Field(default_factory=list)
    runtime_conditions: List[RuntimeConditionSpec] = Field(default_factory=list)
    safety: SafetySpec
    compatibility: CompatibilitySpec
    provenance: ProvenanceSpec


# --- Registry Entries ---

class CapabilityRegistryEntry(BaseModel):
    name: str
    description: str
    latest_version: str
    approved_version: Optional[str] = None
    status: ArtifactStatus = ArtifactStatus.DRAFT
    artifact_path: str
    inputs: List[InputSpec]
    outputs: List[OutputSpec]
    examples: List[str] = Field(default_factory=list)


class CapabilityRegistryFile(BaseModel):
    schema_version: str = Field(default="1")
    capabilities: List[CapabilityRegistryEntry] = Field(default_factory=list)

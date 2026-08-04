"""Provider-neutral governance contracts carried with every workflow."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DataCategory(StrEnum):
    GENERAL_CONTENT = "general_content"
    CONTACT_INFORMATION = "contact_information"
    HEALTH_INFORMATION = "health_information"
    FINANCIAL_INFORMATION = "financial_information"
    PAYMENT_CARD_DATA = "payment_card_data"
    CREDENTIALS = "credentials"
    BIOMETRIC_INFORMATION = "biometric_information"
    CHILDRENS_DATA = "childrens_data"
    EDUCATION_RECORDS = "education_records"
    GOVERNMENT_DATA = "government_data"


class DataClassification(StrEnum):
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED_PERSONAL = "restricted_personal_data"
    REGULATED_HIGH_IMPACT = "regulated_high_impact_data"


class ProcessingPurpose(StrEnum):
    DELIVERY_PLANNING = "delivery_planning"


class ProcessingOperation(StrEnum):
    WORKFLOW_INTAKE = "workflow_intake"
    AGENT_PLANNING = "agent_planning"
    EXTERNAL_MODEL_INFERENCE = "external_model_inference"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    TOOL_EXECUTION = "tool_execution"


class EnforcementMode(StrEnum):
    OBSERVE = "observe"
    WARN = "warn"
    ENFORCE = "enforce"


class PolicyOutcome(StrEnum):
    PERMIT = "permit"
    PERMIT_WITH_CONTROLS = "permit_with_controls"
    DENY = "deny"


class Obligation(StrEnum):
    AUDIT_DECISION = "audit_decision"
    PURPOSE_LIMITATION = "purpose_limitation"
    DATA_MINIMIZATION = "data_minimization"
    REDACT_BEFORE_EXTERNAL_PROCESSING = "redact_before_external_processing"
    LOCAL_PROCESSING_ONLY = "local_processing_only"
    NO_PROVIDER_TRAINING = "no_provider_training"
    HUMAN_APPROVAL_FOR_SIDE_EFFECTS = "human_approval_for_side_effects"
    ENHANCED_ACCESS_LOGGING = "enhanced_access_logging"


class DataProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    classification: DataClassification
    categories: tuple[DataCategory, ...]
    detection_basis: tuple[str, ...] = Field(alias="detectionBasis")


class ProcessingContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str = Field(alias="subjectId")
    tenant_id: str = Field(default="local-reference", alias="tenantId")
    purpose: ProcessingPurpose
    operation: ProcessingOperation
    provider: str
    jurisdiction: str = "US"
    data_profile: DataProfile = Field(alias="dataProfile")
    overlay_ids: tuple[str, ...] = Field(default=("common-us-baseline",), alias="overlayIds")


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(alias="decisionId")
    policy_version: str = Field(alias="policyVersion")
    outcome: PolicyOutcome
    execution_allowed: bool = Field(alias="executionAllowed")
    enforcement_mode: EnforcementMode = Field(alias="enforcementMode")
    classification: DataClassification
    obligations: tuple[Obligation, ...]
    reasons: tuple[str, ...]
    retention_policy: str = Field(alias="retentionPolicy")
    overlay_ids: tuple[str, ...] = Field(alias="overlayIds")

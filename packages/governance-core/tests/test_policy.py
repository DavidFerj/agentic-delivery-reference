"""Common baseline decisions and enforcement modes."""

import pytest
from agentic_governance import BaselinePolicyEngine
from agentic_governance.models import (
    DataCategory,
    DataClassification,
    DataProfile,
    EnforcementMode,
    Obligation,
    PolicyOutcome,
    ProcessingContext,
    ProcessingOperation,
    ProcessingPurpose,
)


def context(
    category: DataCategory,
    *,
    operation: ProcessingOperation = ProcessingOperation.WORKFLOW_INTAKE,
    provider: str = "local-api",
) -> ProcessingContext:
    classifications = {
        DataCategory.GENERAL_CONTENT: DataClassification.INTERNAL,
        DataCategory.CONTACT_INFORMATION: DataClassification.CONFIDENTIAL,
        DataCategory.HEALTH_INFORMATION: DataClassification.RESTRICTED_PERSONAL,
        DataCategory.CREDENTIALS: DataClassification.RESTRICTED_PERSONAL,
        DataCategory.PAYMENT_CARD_DATA: DataClassification.REGULATED_HIGH_IMPACT,
    }
    return ProcessingContext(
        subjectId="requester-1",
        purpose=ProcessingPurpose.DELIVERY_PLANNING,
        operation=operation,
        provider=provider,
        dataProfile=DataProfile(
            classification=classifications[category],
            categories=(category,),
            detectionBasis=("test",),
        ),
    )


@pytest.mark.parametrize(
    "category", [DataCategory.GENERAL_CONTENT, DataCategory.CONTACT_INFORMATION]
)
def test_non_restricted_local_processing_is_permitted(category: DataCategory) -> None:
    decision = BaselinePolicyEngine().evaluate(context(category))

    assert decision.outcome == PolicyOutcome.PERMIT
    assert decision.execution_allowed is True
    assert decision.retention_policy == "standard-90-days"
    assert decision.obligations == (Obligation.AUDIT_DECISION, Obligation.PURPOSE_LIMITATION)


def test_restricted_data_is_permitted_locally_with_controls() -> None:
    decision = BaselinePolicyEngine().evaluate(context(DataCategory.HEALTH_INFORMATION))

    assert decision.outcome == PolicyOutcome.PERMIT_WITH_CONTROLS
    assert decision.execution_allowed is True
    assert decision.retention_policy == "restricted-30-days"
    assert Obligation.LOCAL_PROCESSING_ONLY in decision.obligations
    assert Obligation.HUMAN_APPROVAL_FOR_SIDE_EFFECTS in decision.obligations


@pytest.mark.parametrize("category", [DataCategory.CREDENTIALS, DataCategory.PAYMENT_CARD_DATA])
def test_prohibited_raw_intake_is_denied(category: DataCategory) -> None:
    decision = BaselinePolicyEngine().evaluate(context(category))

    assert decision.outcome == PolicyOutcome.DENY
    assert decision.execution_allowed is False
    assert "prohibited" in decision.reasons[0]


def test_restricted_data_is_denied_for_an_unapproved_external_provider() -> None:
    decision = BaselinePolicyEngine().evaluate(
        context(
            DataCategory.HEALTH_INFORMATION,
            operation=ProcessingOperation.EXTERNAL_MODEL_INFERENCE,
            provider="public-external-model",
        )
    )

    assert decision.outcome == PolicyOutcome.DENY
    assert decision.execution_allowed is False
    assert "unapproved provider" in decision.reasons[0]


@pytest.mark.parametrize("mode", [EnforcementMode.OBSERVE, EnforcementMode.WARN])
def test_legacy_rollout_modes_report_denial_without_blocking(mode: EnforcementMode) -> None:
    decision = BaselinePolicyEngine(mode).evaluate(context(DataCategory.CREDENTIALS))

    assert decision.outcome == PolicyOutcome.DENY
    assert decision.execution_allowed is True
    assert decision.enforcement_mode == mode


def test_identical_context_produces_the_same_traceable_decision() -> None:
    engine = BaselinePolicyEngine()
    processing_context = context(DataCategory.GENERAL_CONTENT)

    first = engine.evaluate(processing_context)
    second = engine.evaluate(processing_context)

    assert first == second
    assert len(first.decision_id) == 64
    assert first.policy_version == "common-us-v1"

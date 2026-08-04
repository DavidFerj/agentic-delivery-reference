"""Versioned common baseline policy evaluated before data processing."""

import hashlib
import json

from agentic_governance.models import (
    DataCategory,
    DataClassification,
    EnforcementMode,
    Obligation,
    PolicyDecision,
    PolicyOutcome,
    ProcessingContext,
    ProcessingOperation,
)

POLICY_VERSION = "common-us-v1"
LOCAL_PROVIDERS = {"local-api", "deterministic-local"}
PROHIBITED_INTAKE = {DataCategory.CREDENTIALS, DataCategory.PAYMENT_CARD_DATA}


class BaselinePolicyEngine:
    """Apply conservative portable controls without inferring legal applicability."""

    def __init__(self, mode: EnforcementMode = EnforcementMode.ENFORCE) -> None:
        self._mode = mode

    def evaluate(self, context: ProcessingContext) -> PolicyDecision:
        categories = set(context.data_profile.categories)
        sensitive = context.data_profile.classification in {
            DataClassification.RESTRICTED_PERSONAL,
            DataClassification.REGULATED_HIGH_IMPACT,
        }
        reasons: list[str] = []
        obligations = {Obligation.AUDIT_DECISION, Obligation.PURPOSE_LIMITATION}

        denied = False
        if context.operation == ProcessingOperation.WORKFLOW_INTAKE and categories.intersection(
            PROHIBITED_INTAKE
        ):
            denied = True
            reasons.append(
                "Raw credentials and payment-card data are prohibited at workflow intake."
            )
        if sensitive and context.provider not in LOCAL_PROVIDERS:
            denied = True
            reasons.append("Restricted data cannot be sent to an unapproved provider.")

        if sensitive:
            obligations.update(
                {
                    Obligation.DATA_MINIMIZATION,
                    Obligation.REDACT_BEFORE_EXTERNAL_PROCESSING,
                    Obligation.LOCAL_PROCESSING_ONLY,
                    Obligation.NO_PROVIDER_TRAINING,
                    Obligation.HUMAN_APPROVAL_FOR_SIDE_EFFECTS,
                    Obligation.ENHANCED_ACCESS_LOGGING,
                }
            )
            retention_policy = "restricted-30-days"
        else:
            retention_policy = "standard-90-days"

        if denied:
            outcome = PolicyOutcome.DENY
        elif len(obligations) > 2:
            outcome = PolicyOutcome.PERMIT_WITH_CONTROLS
            reasons.append("Sensitive data requires the common baseline control set.")
        else:
            outcome = PolicyOutcome.PERMIT
            reasons.append("The common baseline permits this local processing operation.")

        execution_allowed = not denied or self._mode != EnforcementMode.ENFORCE
        canonical = json.dumps(
            {
                "context": context.model_dump(mode="json", by_alias=True),
                "mode": self._mode.value,
                "outcome": outcome.value,
                "policy": POLICY_VERSION,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return PolicyDecision(
            decisionId=hashlib.sha256(canonical.encode()).hexdigest(),
            policyVersion=POLICY_VERSION,
            outcome=outcome,
            executionAllowed=execution_allowed,
            enforcementMode=self._mode,
            classification=context.data_profile.classification,
            obligations=tuple(sorted(obligations, key=str)),
            reasons=tuple(reasons),
            retentionPolicy=retention_policy,
            overlayIds=context.overlay_ids,
        )

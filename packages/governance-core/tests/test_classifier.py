"""Deterministic classification behavior for explicit and detected data."""

import pytest
from agentic_governance.classifier import DeterministicDataClassifier
from agentic_governance.models import DataCategory, DataClassification


@pytest.mark.parametrize(
    ("sample", "category", "classification"),
    [
        (
            "Discuss a patient diagnosis",
            DataCategory.HEALTH_INFORMATION,
            DataClassification.RESTRICTED_PERSONAL,
        ),
        (
            "Use a bank account",
            DataCategory.FINANCIAL_INFORMATION,
            DataClassification.RESTRICTED_PERSONAL,
        ),
        (
            "Never include a credit card",
            DataCategory.PAYMENT_CARD_DATA,
            DataClassification.REGULATED_HIGH_IMPACT,
        ),
        ("Remove the API key", DataCategory.CREDENTIALS, DataClassification.RESTRICTED_PERSONAL),
        (
            "Store a fingerprint",
            DataCategory.BIOMETRIC_INFORMATION,
            DataClassification.RESTRICTED_PERSONAL,
        ),
        (
            "Protect a child profile",
            DataCategory.CHILDRENS_DATA,
            DataClassification.RESTRICTED_PERSONAL,
        ),
        (
            "Export a student record",
            DataCategory.EDUCATION_RECORDS,
            DataClassification.RESTRICTED_PERSONAL,
        ),
        (
            "Handle CUI safely",
            DataCategory.GOVERNMENT_DATA,
            DataClassification.REGULATED_HIGH_IMPACT,
        ),
        (
            "Update an email address",
            DataCategory.CONTACT_INFORMATION,
            DataClassification.CONFIDENTIAL,
        ),
    ],
)
def test_classifier_detects_narrow_sensitive_categories(
    sample: str, category: DataCategory, classification: DataClassification
) -> None:
    profile = DeterministicDataClassifier().classify(sample)

    assert category in profile.categories
    assert profile.classification == classification
    assert f"detected:{category.value}" in profile.detection_basis


def test_classifier_defaults_to_internal_general_content() -> None:
    profile = DeterministicDataClassifier().classify("Prepare a simple delivery plan")

    assert profile.categories == (DataCategory.GENERAL_CONTENT,)
    assert profile.classification == DataClassification.INTERNAL
    assert profile.detection_basis == ("default:general_content",)


def test_declared_and_detected_categories_are_combined_and_deduplicated() -> None:
    profile = DeterministicDataClassifier().classify(
        "Review patient contact information",
        {DataCategory.HEALTH_INFORMATION},
    )

    assert profile.categories == (
        DataCategory.CONTACT_INFORMATION,
        DataCategory.HEALTH_INFORMATION,
    )
    assert profile.detection_basis == (
        "declared:health_information",
        "detected:contact_information",
        "detected:health_information",
    )

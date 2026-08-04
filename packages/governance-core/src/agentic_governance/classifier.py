"""Conservative deterministic classifier for the offline reference profile."""

import re

from agentic_governance.models import DataCategory, DataClassification, DataProfile

PATTERNS: dict[DataCategory, re.Pattern[str]] = {
    DataCategory.HEALTH_INFORMATION: re.compile(
        r"\b(patient|diagnosis|symptoms?|medical record|health information|phi)\b", re.I
    ),
    DataCategory.FINANCIAL_INFORMATION: re.compile(
        r"\b(bank account|credit report|financial account)\b", re.I
    ),
    DataCategory.PAYMENT_CARD_DATA: re.compile(
        r"\b(credit card|card number|cardholder|cvv|payment card)\b", re.I
    ),
    DataCategory.CREDENTIALS: re.compile(
        r"\b(password|api key|access token|private key|login credential)\b", re.I
    ),
    DataCategory.BIOMETRIC_INFORMATION: re.compile(
        r"\b(fingerprint|face template|iris scan|voiceprint|biometric)\b", re.I
    ),
    DataCategory.CHILDRENS_DATA: re.compile(r"\b(child|children|minor|under 13)\b", re.I),
    DataCategory.EDUCATION_RECORDS: re.compile(
        r"\b(student record|education record|school transcript)\b", re.I
    ),
    DataCategory.GOVERNMENT_DATA: re.compile(
        r"\b(controlled unclassified|government restricted|cui)\b", re.I
    ),
    DataCategory.CONTACT_INFORMATION: re.compile(
        r"\b(email address|phone number|home address|contact information)\b", re.I
    ),
}

CLASSIFICATION_BY_CATEGORY: dict[DataCategory, DataClassification] = {
    DataCategory.GENERAL_CONTENT: DataClassification.INTERNAL,
    DataCategory.CONTACT_INFORMATION: DataClassification.CONFIDENTIAL,
    DataCategory.HEALTH_INFORMATION: DataClassification.RESTRICTED_PERSONAL,
    DataCategory.FINANCIAL_INFORMATION: DataClassification.RESTRICTED_PERSONAL,
    DataCategory.CREDENTIALS: DataClassification.RESTRICTED_PERSONAL,
    DataCategory.BIOMETRIC_INFORMATION: DataClassification.RESTRICTED_PERSONAL,
    DataCategory.CHILDRENS_DATA: DataClassification.RESTRICTED_PERSONAL,
    DataCategory.EDUCATION_RECORDS: DataClassification.RESTRICTED_PERSONAL,
    DataCategory.PAYMENT_CARD_DATA: DataClassification.REGULATED_HIGH_IMPACT,
    DataCategory.GOVERNMENT_DATA: DataClassification.REGULATED_HIGH_IMPACT,
}

CLASSIFICATION_ORDER = {
    DataClassification.INTERNAL: 0,
    DataClassification.CONFIDENTIAL: 1,
    DataClassification.RESTRICTED_PERSONAL: 2,
    DataClassification.REGULATED_HIGH_IMPACT: 3,
}


class DeterministicDataClassifier:
    """Combine explicit metadata with narrow local detection rules."""

    def classify(
        self, text: str, declared_categories: set[DataCategory] | None = None
    ) -> DataProfile:
        categories = set(declared_categories or ())
        basis = [f"declared:{category.value}" for category in sorted(categories, key=str)]
        for category, pattern in PATTERNS.items():
            if pattern.search(text):
                categories.add(category)
                basis.append(f"detected:{category.value}")
        if not categories:
            categories.add(DataCategory.GENERAL_CONTENT)
            basis.append("default:general_content")

        classification = max(
            (CLASSIFICATION_BY_CATEGORY[category] for category in categories),
            key=CLASSIFICATION_ORDER.__getitem__,
        )
        return DataProfile(
            classification=classification,
            categories=tuple(sorted(categories, key=str)),
            detectionBasis=tuple(sorted(set(basis))),
        )

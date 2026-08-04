"""Versioned local knowledge and a replaceable deterministic retrieval boundary."""

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from agentic_runtime.models import Category

TOKEN = re.compile(r"[a-z0-9]{3,}")


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    document_id: str
    title: str
    section: str
    version: str
    content: str
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievedPassage:
    document: KnowledgeDocument
    relevance_score: float

    @property
    def content_hash(self) -> str:
        return sha256(self.document.content.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetrievalBatch:
    corpus_version: str
    passages: tuple[RetrievedPassage, ...]


class KnowledgeRetriever(Protocol):
    def retrieve(self, query: str, category: Category) -> RetrievalBatch: ...


LOCAL_CORPUS = (
    KnowledgeDocument(
        "delivery-quality-v1",
        "Delivery quality baseline",
        "quality-gates",
        "1.0.0",
        "Define explicit contracts, test failure modes, and retain reproducible evidence.",
        ("general", "quality", "delivery"),
    ),
    KnowledgeDocument(
        "integration-boundary-v1",
        "Integration boundary guide",
        "provider-adapters",
        "1.0.0",
        "Keep provider authentication, timeouts, retries, and error mapping "
        "behind a typed adapter.",
        ("integration", "api", "provider", "webhook"),
    ),
    KnowledgeDocument(
        "security-boundary-v1",
        "Security boundary guide",
        "trust-boundaries",
        "1.0.0",
        "Threat-model identity, authorization, secrets, and every external trust boundary.",
        ("security", "auth", "permission", "secret"),
    ),
    KnowledgeDocument(
        "data-change-v1",
        "Data change guide",
        "migration-safety",
        "1.0.0",
        "Define schema compatibility, transactional consistency, rollback, "
        "and retention before migration.",
        ("data", "database", "schema", "migration"),
    ),
)


class LocalKnowledgeRetriever:
    """Rank an allowlisted synthetic corpus without embeddings or network calls."""

    def __init__(
        self,
        documents: tuple[KnowledgeDocument, ...] = LOCAL_CORPUS,
        *,
        corpus_version: str = "local-delivery-corpus-v1",
        top_k: int = 2,
    ) -> None:
        self._documents = documents
        self._corpus_version = corpus_version
        self._top_k = top_k

    def retrieve(self, query: str, category: Category) -> RetrievalBatch:
        query_tokens = set(TOKEN.findall(query.lower()))
        ranked: list[RetrievedPassage] = []
        for document in self._documents:
            document_tokens = set(TOKEN.findall(document.content.lower())) | set(document.tags)
            overlap = len(query_tokens & document_tokens)
            category_bonus = 3 if category in document.tags else 0
            general_bonus = 1 if "general" in document.tags else 0
            raw_score = overlap + category_bonus + general_bonus
            if raw_score:
                ranked.append(RetrievedPassage(document, min(1.0, round(raw_score / 5, 3))))
        ranked.sort(key=lambda item: (-item.relevance_score, item.document.document_id))
        return RetrievalBatch(self._corpus_version, tuple(ranked[: self._top_k]))

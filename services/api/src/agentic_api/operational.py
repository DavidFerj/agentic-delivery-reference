"""Sanitized local telemetry, redaction, and abuse-control adapters."""

import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from time import monotonic
from typing import Any

SENSITIVE_FIELDS = frozenset(
    {
        "authorization",
        "cookie",
        "credential",
        "idempotencykey",
        "password",
        "prompt",
        "request",
        "secret",
        "token",
    }
)
SENSITIVE_VALUES = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._-]+"),
    re.compile(r"(?i)\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*\S+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)
REDACTED = "[REDACTED]"


def _normalized_field(name: object) -> str:
    return re.sub(r"[^a-z]", "", str(name).lower())


def redact_sensitive(value: Any, field_name: object | None = None) -> Any:
    """Recursively redact allowlisted field names and credential-shaped strings."""

    if field_name is not None and _normalized_field(field_name) in SENSITIVE_FIELDS:
        return REDACTED
    if isinstance(value, Mapping):
        return {key: redact_sensitive(item, key) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for pattern in SENSITIVE_VALUES:
            redacted = pattern.sub(REDACTED, redacted)
        return redacted
    return value


@dataclass(frozen=True, slots=True)
class RequestObservation:
    occurred_at: datetime
    method: str
    route: str
    status_code: int
    duration_ms: float
    correlation_id: str


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    total_requests: int
    error_requests: int
    average_duration_ms: float
    status_counts: dict[str, int]
    route_counts: dict[str, int]
    recent_requests: tuple[RequestObservation, ...]


class InMemoryOperationalTelemetry:
    """Collect allowlisted request metadata without payloads or headers."""

    def __init__(self, now_factory: Callable[[], datetime] | None = None) -> None:
        self._now_factory = now_factory or (lambda: datetime.now(UTC))
        self._lock = RLock()
        self._observations: list[RequestObservation] = []

    def record(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_ms: float,
        correlation_id: str,
    ) -> None:
        with self._lock:
            self._observations.append(
                RequestObservation(
                    occurred_at=self._now_factory(),
                    method=method,
                    route=route,
                    status_code=status_code,
                    duration_ms=max(0.0, round(duration_ms, 3)),
                    correlation_id=correlation_id,
                )
            )

    def snapshot(self, recent_limit: int = 20) -> TelemetrySnapshot:
        with self._lock:
            observations = tuple(self._observations)
        total = len(observations)
        average = sum(item.duration_ms for item in observations) / total if total else 0.0
        return TelemetrySnapshot(
            total_requests=total,
            error_requests=sum(item.status_code >= 400 for item in observations),
            average_duration_ms=round(average, 3),
            status_counts=dict(Counter(str(item.status_code) for item in observations)),
            route_counts=dict(Counter(item.route for item in observations)),
            recent_requests=observations[-recent_limit:],
        )


@dataclass(slots=True)
class _RateWindow:
    started_at: float
    requests: int


class InMemoryRateLimiter:
    """Apply a process-local fixed window to a verified principal."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._lock = RLock()
        self._windows: dict[str, _RateWindow] = {}

    def allow(self, subject: str) -> bool:
        now = self._clock()
        with self._lock:
            window = self._windows.get(subject)
            if window is None or now - window.started_at >= self._window_seconds:
                self._windows[subject] = _RateWindow(now, 1)
                return True
            if window.requests >= self._limit:
                return False
            window.requests += 1
            return True

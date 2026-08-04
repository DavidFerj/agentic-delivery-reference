"""Authentication and request metadata validation at the HTTP boundary."""

import re
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agentic_api.domain import Principal
from agentic_api.errors import (
    AuthenticationRequired,
    InvalidRequestMetadata,
    RequestRateExceeded,
)
from agentic_api.operational import InMemoryRateLimiter
from agentic_api.ports import IdentityProvider

METADATA_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
bearer_scheme = HTTPBearer(auto_error=False)


def get_identity_provider(request: Request) -> IdentityProvider:
    return cast(IdentityProvider, request.app.state.identity_provider)


def authenticated_principal(
    provider: Annotated[IdentityProvider, Depends(get_identity_provider)],
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    principal = provider.verify(credential.credentials) if credential else None
    if principal is None:
        raise AuthenticationRequired("A valid bearer credential is required.")
    return principal


def correlation_id(
    request: Request,
    value: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> str:
    if value is None:
        generated = getattr(request.state, "correlation_id", None) or str(uuid4())
        request.state.correlation_id = generated
        return cast(str, generated)
    if not METADATA_PATTERN.fullmatch(value):
        raise InvalidRequestMetadata("X-Correlation-ID has an invalid format.")
    request.state.correlation_id = value
    return value


def idempotency_key(
    value: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if value is None or len(value) < 8 or not METADATA_PATTERN.fullmatch(value):
        raise InvalidRequestMetadata("Idempotency-Key must contain 8 to 128 safe characters.")
    return value


def enforce_mutation_rate_limit(
    request: Request,
    principal: Annotated[Principal, Depends(authenticated_principal)],
) -> None:
    limiter = cast(InMemoryRateLimiter, request.app.state.rate_limiter)
    if not limiter.allow(principal.subject):
        raise RequestRateExceeded(
            "The local mutation limit was reached. Retry after the configured window."
        )

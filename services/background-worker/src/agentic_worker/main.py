"""Private worker HTTP process foundation."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict


class WorkerHealthResponse(BaseModel):
    """Private worker liveness response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    service: Literal["background-worker"] = "background-worker"


def create_app() -> FastAPI:
    """Build the private worker process without task handlers yet."""

    application = FastAPI(
        title="Agentic Delivery Background Worker",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @application.get("/health", response_model=WorkerHealthResponse, include_in_schema=False)
    def health() -> WorkerHealthResponse:
        return WorkerHealthResponse()

    return application


app = create_app()

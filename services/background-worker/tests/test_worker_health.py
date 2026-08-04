"""Private worker liveness tests."""

from fastapi.testclient import TestClient

from agentic_worker.main import create_app


def test_worker_health_is_minimal() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "background-worker"}


def test_worker_does_not_publish_documentation_or_task_placeholder() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 404
        assert client.post("/tasks/execute").status_code == 404

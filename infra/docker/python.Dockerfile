FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md LICENSE ./
COPY requirements ./requirements
COPY services ./services
COPY packages/governance-core ./packages/governance-core
COPY evaluations ./evaluations

RUN python -m pip install --upgrade pip \
    && python -m pip install --constraint requirements/production.txt .

USER app

EXPOSE 8080

CMD ["uvicorn", "agentic_api.main:app", "--host", "0.0.0.0", "--port", "8080"]

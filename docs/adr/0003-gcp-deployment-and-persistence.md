# ADR-0003: GCP Deployment and Operational Persistence

- Status: Accepted
- Date: 2026-08-03

## Context

The target platform includes Cloud Run, Firebase Authentication, Firestore, Cloud Tasks, Cloud Storage, Secret Manager, and later analytical export.

## Decision

Deploy web and API as public Cloud Run services, the worker as a private authenticated Cloud Run service, and evaluation as a Cloud Run Job. Store operational records in Firestore through repository ports and artifacts in Cloud Storage. Deliver asynchronous commands through a queue port implemented by Cloud Tasks in cloud. Use Terraform and separate GCP projects for development, staging, and any future production environment.

The API validates Firebase/OIDC identity and enforces application authorization. Every deployable uses a distinct service account.

## Consequences

- Managed, container-based scaling keeps platform operations small.
- Firestore transaction and contention behavior must be tested for workflow versions and approval consumption.
- The public API requires robust application authentication, authorization, abuse controls, and safe error handling.
- Local emulators or adapters must preserve cloud-visible behavior.

# Triagely — AI-assisted vulnerability triage (MVP)

A runnable starter for a team vulnerability-triage workspace. This MVP includes:
- FastAPI API with findings, workflow transitions, comments/evidence notes and SARIF import
- PostgreSQL-ready SQLAlchemy models (SQLite works out of the box)
- Redis/Celery worker scaffold for asynchronous verification
- React + TypeScript dashboard with filtering, status workflow, severity chart and MTTR summary
- Docker Compose for local development

## Quick start

### Requirements
Docker Desktop (recommended), or Python 3.11+ and Node 20+.

### Start API + database + Redis + worker
```bash
cp .env.example .env
docker compose up --build
```
API: http://localhost:8000  
Swagger: http://localhost:8000/docs  
Frontend: http://localhost:5173

The API creates tables on startup for this MVP. For a real deployment, add Alembic migrations.

### Add sample findings
```bash
curl -X POST http://localhost:8000/findings/demo
```

### Import SARIF
```bash
curl -X POST http://localhost:8000/findings/import/sarif \
  -H "Content-Type: application/json" \
  --data-binary @sample.sarif
```

## API overview
- `GET /findings` — list/filter findings
- `POST /findings` — create a finding
- `GET /findings/{id}` — details
- `PATCH /findings/{id}/status` — transition status
- `POST /findings/{id}/notes` — add evidence note
- `POST /findings/import/sarif` — import SARIF 2.1.0 results
- `GET /metrics` — severity counts and mean time to resolve

## Important security boundary

The verifier in this starter is deliberately **stubbed**. It records a verification job but does not execute untrusted proof-of-concept code. Do not add `docker.sock` access or run submitted code in the API/worker container. A production verifier should use a separately isolated runner (preferably gVisor/Kata or a hardened ephemeral VM), with no secrets, no network by default, strict CPU/memory/time limits, read-only base filesystem, and disposable storage. Treat scanner output and LLM output as untrusted input.

## Roadmap to production
1. Add authentication (OIDC), organizations, project membership and RBAC.
2. Add Alembic migrations, audit log and tenant isolation.
3. Implement GitHub App installation/webhooks and GitHub Actions upload.
4. Add Semgrep/pip-audit execution in CI and SARIF ingestion.
5. Add safe verifier runner as a separate service with a narrow signed job protocol.
6. Add LLM provider adapter with JSON schema validation, prompt-injection defenses and human approval.
7. Add Yjs collaboration provider with persistence, room authorization and WebSocket scaling.
8. Add deduplication using normalized fingerprints/rule IDs first; embeddings as a secondary signal.
9. Build a labelled evaluation dataset and calculate precision/recall with confidence intervals.

This repository is a development foundation, not a production security product.

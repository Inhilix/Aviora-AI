# AvioraAI Platform

Self-hosted study-abroad advising platform for Bangladeshi students. FastAPI + Celery
backend, React frontend, Postgres/pgvector, Redis, and a Haiku-powered LLM layer with
strict cost controls, PII stripping, and a 4-stage guardrail pipeline.

## Architecture

```
nginx (TLS, rate limiting)
 ├── frontend (React/Vite SPA, served via nginx)
 └── fastapi (8 workers)
      ├── postgres (+ pgvector for RAG)
      ├── redis (rate limits, token budgets, pub/sub streaming, Celery broker)
      ├── guardrail (sentence-transformers — topic + injection classification)
      └── celery workers (queues: default, llm, alerts) + celery-beat
prometheus + grafana (internal monitoring)
NAS (NFS mount for document storage + Postgres backups)
```

## First-time setup

1. **Generate JWT keypair**
   ```bash
   openssl genrsa -out private.pem 2048
   openssl rsa -in private.pem -pubout -out public.pem
   ```
   Paste contents into `.env` as `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`.

2. **Generate AES master key**
   ```bash
   openssl rand -hex 32
   ```

3. **Copy and fill in environment**
   ```bash
   cp .env.example .env
   # Fill in: DB password, ANTHROPIC_API_KEY, NAS_IP, SMTP creds, DOMAIN
   ```

4. **TLS certificates** — place `fullchain.pem` and `privkey.pem` in `nginx/certs/`
   (e.g. via certbot / Let's Encrypt).

5. **Build and start**
   ```bash
   docker compose up -d --build
   ```

6. **Run migrations**
   ```bash
   docker compose exec fastapi bash scripts/init_db.sh
   ```

7. **Seed the RAG knowledge base** (visa/admission content for UK, Canada, Australia, Germany)
   ```bash
   docker compose exec fastapi python scripts/seed_knowledge.py
   ```

8. **Create an admin user** — register normally via `/api/auth/register`, then:
   ```sql
   UPDATE students SET is_admin = TRUE WHERE email = 'you@example.com';
   ```

## Cost & rate-limit controls 

| Control | Where | Limit |
|---|---|---|
| Per-user daily token budget | Redis, `check_and_consume_token_budget` | 50,000 tokens/day (configurable) |
| Global daily cost ceiling | Redis, `check_daily_cost_ceiling` | $5.00/day — returns 503 when hit |
| LLM endpoint rate limit | nginx + SlowAPI | 3-5/min, scaling to /hour and /day |
| Auth endpoint rate limit | nginx | 5/min |
| General API rate limit | nginx | 30/min |

All Haiku calls go through `call_haiku_safe()` which enforces cost ceiling → PII
stripping → token budget → call → cost recording, in that order.

## Guardrail pipeline 

Four stages, all must pass before any LLM call:
1. **Regex fast-check** — known jailbreak/injection phrasings (~0ms)
2. **Semantic injection check** — sentence-transformer similarity vs known injection phrases
3. **Topic relevance check** — must be semantically close to study-abroad topics
4. **Violation accumulator** — 3 violations/hour → soft block; 5 total → admin flag in audit log

The guardrail container fails **closed**: if unreachable, requests are rejected (503),
never silently passed through.

## Anti-sycophancy 

`evaluate_profile_with_llm()` runs two passes:
- Pass 1: LLM assessment anchored to a deterministic rubric score (computed in
  `profile_scorer.py`, zero LLM involvement)
- Pass 2: LLM self-critiques pass 1 for omitted weaknesses

Profiles scoring below 40/100 get a hardcoded `PROFILE_NOT_VIABLE` verdict regardless
of what the LLM says — the rubric floor cannot be talked around.

## Data retention 

- Students inactive 5 years → notified, then crypto-erased 60 days later
  (`app/tasks/data_deletion.py`, runs daily via celery-beat)
- Self-service deletion: `DELETE /api/students/me` deactivates immediately,
  permanent erase after a 30-day grace period (cancel by logging back in)
- `audit_logs` table is append-only (DB trigger blocks UPDATE/DELETE)

## RAG knowledge base 

`knowledge_base` table uses pgvector (768-dim, all-MiniLM-L6-v2 embeddings via the
guardrail container's `/embed` endpoint). Seeded with visa/checklist/SOP guidance for
UK, Canada, Australia, Germany + general topics. Add more via `seed_knowledge_base()`
in `app/services/rag.py`.

`/api/visa/ask` retrieves top-5 chunks by cosine similarity, injects them into the
Haiku prompt, and returns the answer plus cited source topics — grounded answers only,
explicitly told not to fabricate beyond the references.

## Streaming SOP generation

`/api/sop/generate` queues a Celery task and returns a `task_id` immediately.
The frontend opens an SSE connection to `/api/sop/stream/{task_id}`, which subscribes
to a Redis pub/sub channel that the Celery worker publishes chunks to as Haiku streams
its response. Final result also cached in Redis for polling via `/api/sop/tasks/{task_id}`.

## Load testing 

```bash
pip install locust
locust -f scripts/load_test.py --users 100 --spawn-rate 10 --host https://yourdomain.com
```

Pass criteria: P50 < 200ms for rule-based endpoints, P95 < 15s for LLM endpoints,
zero 5xx errors, total memory < 40GB.

## Monitoring

Grafana at `/grafana` (provisioned dashboard "StudyAI — Cost & Usage Overview" covers
daily LLM cost, request rates, guardrail verdicts, P95 latency on LLM endpoints,
per-user token usage, and infra health). Prometheus scrapes `/api/metrics` (FastAPI,
via `prometheus-fastapi-instrumentator`).

## Directory structure

```
backend/app/
  models/        SQLAlchemy ORM (10 tables)
  schemas/       Pydantic request/response models
  routers/       auth, students, profiles, universities, applications,
                 documents, sop, interview, visa, admin
  security/      JWT, rate limiting, cost guard, PII stripping
  guardrail/     4-stage classifier client
  agents/        Haiku wrapper, anti-sycophancy eval, intent router
  services/      profile_scorer (rubric), rag (pgvector retrieval)
  tasks/         celery_app, sop_tasks (streaming), deadline_alerts,
                 data_deletion
  alembic/       migrations
guardrail/        standalone sentence-transformers classifier + embedder
frontend/src/
  pages/          Login, Register, Dashboard, ProfileForm, Universities,
                  Documents, SopGenerator, MockInterview, VisaGuidance
  components/     Layout (sidebar nav)
  hooks/          useSopStream (SSE)
  api/            axios client with refresh-token interceptor
scripts/          init_db.sh, seed_knowledge.py, load_test.py
monitoring/       prometheus.yml, grafana provisioning + dashboard
```

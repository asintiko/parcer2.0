# Audit Report - parcer2.0

## Codebase Map
- FastAPI entrypoint: `backend/api/main.py` includes auth, transactions, analytics, reference, automation, and userbot routers.
- Async processing: `backend/workers/celery_worker.py` (Celery task + Redis consumer) fed by `backend/ingestion/telegram_bot.py` (manual bot) and `backend/ingestion/telegram_userbot.py` (MTProto listener).
- Parsing stack: `backend/parsers/parser_orchestrator.py` orchestrates `regex_parser.py` (regex formats), `gpt_parser.py` (OpenAI fallback), and `operator_mapper.py` (DB-backed mapping).
- Persistence: `backend/database/connection.py` (SQLAlchemy engine/session) and `backend/database/models.py` (Transaction, Check, OperatorMapping, etc.).
- API routes: `backend/api/routes/transactions.py` (CRUD over checks), `analytics.py` (metrics from transactions), `reference.py` (operator catalog), `automation.py` (AI mapping suggestions), `auth.py`/`userbot.py` (auth + bot config).
- Frontend: Vite React app (`frontend/src/main.tsx`) with data table (`frontend/src/components/TransactionTable.tsx`) and API client (`frontend/src/services/api.ts`).

## Findings
### Critical
- `backend/services/auth_service.py:30-33` – Syntax error (`return await aio    redis.from_url(...)`) stops the module from importing, so `/api/auth/*` routes cannot start (confirmed by `compileall`). Fix the call to `aioredis.from_url(...)` and add a smoke test that imports `auth_service`.

### High
- `backend/api/routes/transactions.py:121-173` & `backend/workers/celery_worker.py:44-114` – API endpoints operate on the legacy `Check` table while ingestion writes to `Transaction`; newly parsed receipts never surface to `/api/transactions` or automation, and analytics uses the other table. Align on a single table (prefer `Transaction`) or add synchronization when ingesting.
- `backend/parsers/parser_orchestrator.py:15-18` with `backend/parsers/gpt_parser.py:30-35` – GPT parser is instantiated unconditionally and raises when `OPENAI_API_KEY` is missing, causing `process_receipt_task` to fail/retry even when regex could parse. Lazily instantiate GPT only on fallback and short-circuit to regex-only mode if no API key is configured.
- `backend/workers/celery_worker.py:44-133` & `backend/database/models.py:22-69` – No idempotency/uniqueness (no unique index on `source_chat_id/source_message_id`) and Celery retries after a partial commit will insert duplicates. Add a unique constraint/fingerprint check before insert and handle retries via upsert or skip-on-duplicate logic.

### Medium
- `backend/parsers/regex_parser.py:30-49,137-200` – Regexes assume 2-digit years and `[\d\.]+` amounts; `normalize_amount` turns `"400.000,00"` into an invalid `Decimal`, rejecting common thousand/decimal separators. Broaden patterns to accept both dot/comma thousand/decimal separators and 4-digit years, and normalize by stripping separators before `Decimal`.
- `backend/api/routes/analytics.py:40-47` vs `backend/database/models.py:42` – Uses naive `datetime.now()` against tz-aware `parsed_at`; Postgres can error or mis-filter around offsets. Use timezone-aware `datetime.now(pytz.UTC)`/`datetime.now(tz=...)` and normalize queries.
- `backend/database/connection.py:49-62` & `backend/api/routes/automation.py:286-327` – `get_db_session` never closes and the automation background task reuses the request session long after response, leaking connections and sharing state across async work. Convert dependency to yield-based session management and open/close a new session inside `process_transactions_batch`.
- `backend/parsers/operator_mapper.py:26-76` – Substring matching with ties on equal priority makes mappings non-deterministic for overlapping patterns; cache never refreshes after DB updates. Add deterministic ordering (secondary sort) or explicit regex boundaries, and refresh cache when mappings change.
- `backend/workers/celery_worker.py:44-133` & `backend/ingestion/telegram_userbot.py:66-101` – Redis consumer pops messages with no ack/backoff; coupled with no fingerprinting, transient errors drop messages or double-count on retries. Consider using reliable Celery queue end-to-end or tracking message fingerprints to skip repeats.

### Low
- `frontend/src/components/EditableCell.tsx:8-115`, `frontend/src/components/TransactionTable.tsx:146-854`, `frontend/src/hooks/useHistory.ts:4-7`, etc. – ESLint fails (`no-explicit-any`, missing hook deps) after `npm run lint`; type gaps reduce safety. Tighten typings, add hook deps, and rerun lint.
- `backend/api/routes/automation.py:69-84` – AI suggestion storage is in-memory; tasks/results vanish on restart and are not multi-instance safe. Persist to DB/Redis if these suggestions are needed operationally.

## Static Checks
- `python3 -m compileall backend` → fails on `backend/services/auth_service.py:32` (SyntaxError).
- `python3 -m pytest` (backend) → exit 5, no tests collected.
- `npm run lint` (frontend) → failed with 29 errors/6 warnings (type-safety and hook deps).
- `npm run build` (frontend) → passed (`tsc` + Vite); large bundle warning (>500 kB chunk).

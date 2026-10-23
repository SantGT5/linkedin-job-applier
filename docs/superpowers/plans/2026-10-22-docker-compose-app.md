# LinkedIn Auto-Apply Bot → Docker Compose App Implementation Plan

> **For agentic workers:** Executed by the Maestri team: Developer (codename Lathe) implements, Tester (codename Kestrel) verifies in the browser after each milestone. Steps use checkbox (`- [ ]`) syntax for tracking. Backend tasks: superpowers:test-driven-development, superpowers:systematic-debugging, superpowers:verification-before-completion. Frontend tasks: frontend-design + ui-ux-pro-max. Library docs: context7.

**Goal:** Turn the script-based bot into a local Docker Compose app (React UI + Python api/worker + postgres) where all config is edited in the UI and used by the next run, the bot is watched/steered through noVNC, history and HR emails live in the DB.

**Architecture:** One Python codebase in `backend/` provides `app/` (FastAPI api, DB models, settings schema, seed, worker) and `bot/` (the existing bot, moved). The worker launches the bot as a fresh subprocess per run, after writing a JSON config snapshot from postgres; the bot's `config/*.py` become loaders that read that snapshot (secrets from env). Blocking popups are bridged to the UI through a `prompts` table. The frontend is a Vite SPA served by nginx, which also proxies `/api` to the api and `/novnc` to the worker behind the api's auth check.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, SQLAlchemy 2 (sync), Alembic, psycopg 3, pydantic v2 / pydantic-settings, pytest + httpx; undetected-chromedriver + Debian arm64 `chromium` / `chromium-driver`, Xvfb, x11vnc, noVNC/websockify, PyAutoGUI (+ python3-tk, python3-xlib); React 18 + Vite + TypeScript, react-router, @tanstack/react-query, Tailwind CSS, Vitest + Testing Library; postgres 16; nginx.

**Spec:** `docs/superpowers/specs/2026-10-22-docker-compose-app-design.md` (approved, all ADD/REMOVE items approved).

## Global Constraints

- Layout: `frontend/`, `backend/`, `docker/compose.yaml`, `docker/stack/*.Dockerfile`, `Makefile` with targets `up, down, logs, test, seed, migrate, shell-api, shell-worker, shell-db, backup, restore`.
- `make up` from a clean clone must work (create `.env` from `.env.example` when missing).
- All published ports bind to `127.0.0.1`. Only nginx (frontend) is published: `127.0.0.1:8080`.
- Secrets live only in `.env`: `LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD`, `CLAUDE_API_KEY`, `GLM_API_KEY`, `UI_PASSWORD`, `SESSION_SECRET`, `POSTGRES_PASSWORD`. Never in DB, API responses, logs or the repo. UI shows "set / not set" only.
- Settings edited in the UI take effect on the **next** bot run.
- Existing 42 tests keep passing (moved to `backend/tests/bot/`).
- Seed parses `config/*.py` with `ast` — never imports them.
- Host is Apple Silicon: worker uses native arm64 Chromium, not amd64 Chrome.
- Never commit; leave all changes uncommitted for the owner.
- Throwaway scripts/screenshots in `/tmp`, never the repo.

## Review Focus

1. Bot subprocess crashes or Chrome fails to start → run row ends `failed` with the error, worker returns to idle, UI shows it; never stuck "running". (Task 6 test `test_crashing_bot_marks_run_failed`.)
2. Stop pressed while the bot is waiting on a prompt → bot exits within 5 s, open prompt is closed. (Task 6 test `test_stop_while_waiting_closes_prompt`.)
3. Start clicked twice / from two tabs → exactly one run. (Task 5 test `test_start_twice_creates_one_run`.)
4. Saving a setting with the wrong type (`desired_salary="abc"`, unknown enum) → 422 naming the field, nothing saved. (Task 3 test `test_invalid_setting_rejected_nothing_saved`.)
5. Seed run twice, or CSVs with duplicate Job IDs / missing columns / bad encoding → idempotent, no duplicates, bad rows counted and reported, no crash. (Task 4 tests `test_seed_is_idempotent`, `test_seed_skips_bad_rows`.)

---

## Milestone 1 — Restructure, settings, DB, seed

### Task 1: Move the bot into `backend/bot/` and keep tests green

**Files:**
- Move: `runAiBot.py` → `backend/bot/runAiBot.py`; `modules/` → `backend/bot/modules/`
- Move: `tests/` → `backend/tests/bot/` (fixtures included); `backend/tests/bot/conftest.py` inserts `backend/bot` on `sys.path`
- Create: `backend/pyproject.toml` (deps from Tech Stack + `undetected-chromedriver==3.5.5`, `PyAutoGUI==0.9.54`, `anthropic==0.112.0`, `openai==2.38.0` (GLM uses the OpenAI SDK), `setuptools`; dev: `pytest`, `lxml`, `httpx`), `backend/pytest.ini` (`testpaths = tests`)
- Leave in place: top-level `config/*.py` (seed source only, untouched)

- [ ] Move files with `mv` (not git mv, nothing staged). Fix import paths only where needed.
- [ ] Run `cd backend && python -m pytest tests/bot -q` → expected `42 passed`.

### Task 2: Settings schema + bot config loaders

**Files:**
- Create: `backend/app/settings_schema.py`
- Create: `backend/bot/config/{__init__,_loader,personals,questions,search,secrets,settings}.py`
- Test: `backend/tests/app/test_settings_schema.py`, `backend/tests/bot/test_config_loader.py`

**Interfaces:**
- Produces: `Field` dataclass `(section: str, key: str, type: Literal["str","text","int","bool","list","enum","multi_enum","answers"], default: Any, options: list[str] | None, help: str, min: int | None = None, max: int | None = None)`; `SCHEMA: list[Field]`; `SECTIONS = ("personals","questions","search","settings","ai","email")`; `defaults() -> dict[str, dict[str, Any]]`; `validate(section: str, values: dict) -> dict` (raises `SettingsError(field_errors: dict[str,str])`); `SECRET_ENV: dict[str, str]` mapping bot names → env vars (`username→LINKEDIN_USERNAME`, `password→LINKEDIN_PASSWORD`, `claude_api_key→CLAUDE_API_KEY`, `glm_api_key→GLM_API_KEY`).
- Produces (bot): `config._loader.load(section: str) -> dict` reading `APPLIER_CONFIG_FILE` JSON (`{section: {key: value}}`), falling back to `defaults()`; each `config/<module>.py` does `globals().update(load("<section>"))`. `config/secrets.py` = `load("ai")` + secrets from env via `SECRET_ENV`.

Schema content: every variable in today's `config/*.py`, same names and types, enum options copied from each variable's inline comment, help text from the comment — **minus** removed ones: `llm_api_url, llm_api_key, llm_model, llm_spec, stream_output, keep_screen_awake, ai_log_email_apply, generated_resume_path, file_name, failed_file_name, email_apply_file_name, logs_folder_path, default_resume_path`. `ai_provider` options: `["claude","glm"]`. Non-secret items of `secrets.py` (`use_AI, ai_provider, claude_model, glm_model, glm_reasoning_effort, glm_api_url`) go in section `ai`. New fields: section `email`: `my_name`, `phone_number`, `linkedin_profile` (str, default empty), `subject_template` (str, default `"{job_title} - {my_name}"`), `body_template` (text, default = spec body with `{job_title}`, `{job_url}` placeholders); section `questions`: `custom_answers` (type `answers`: list of `{"match": str, "answer": str}`, default `[]`). Fixed paths come from env in the bot, not settings: `DATA_DIR` (default `/data`) → resume `DATA_DIR/resumes/default/resume.pdf`, logs `DATA_DIR/logs/`.

- [ ] Tests: `test_defaults_cover_every_section`, `test_validate_coerces_and_rejects` (`validate("questions", {"desired_salary": "abc"})` raises with key `desired_salary`; `validate("search", {"date_posted": "Yesterday"})` raises; `validate("ai", {"ai_provider": "glm"})` ok), `test_removed_settings_absent` (none of the removed names in SCHEMA), `test_loader_reads_snapshot` (tmp JSON with `search.search_terms=["X"]` → `config.search.search_terms == ["X"]` via fresh import), `test_loader_defaults_without_snapshot`, `test_secrets_from_env` (monkeypatch `LINKEDIN_PASSWORD`).
- [ ] Implement; run `pytest tests -q` → all pass (incl. the 42).

### Task 3: DB models, migrations, auth, settings API

**Files:**
- Create: `backend/app/{config.py,db.py,models.py,auth.py,main.py}`, `backend/app/api/{settings.py,health.py}`, `backend/alembic.ini`, `backend/migrations/` (initial revision)
- Test: `backend/tests/app/conftest.py` (test DB from `TEST_DATABASE_URL`, transaction rollback per test, `client` fixture logged in), `test_auth.py`, `test_settings_api.py`

**Interfaces:**
- `app.config.Env` (pydantic-settings): `database_url, ui_password, session_secret, data_dir="/data"`, plus secret vars (optional).
- Tables (`app.models`): `settings(section PK, values JSONB, updated_at)`; `runs(id, status: queued|running|waiting|stopping|finished|failed|stopped, started_at, ended_at, error, applied_count, failed_count, skipped_count)`; `run_logs(id, run_id FK, ts, line)`; `bot_control(id=1, desired: running|stopped, updated_at)`; `prompts(id, run_id, title, text, buttons JSONB, answer NULL, created_at, answered_at)`; `applied_jobs(job_id PK, title, company, work_location, work_style, about_job, experience_required, skills, hr_name, hr_link, resume, reposted, date_posted, date_applied, job_link, external_job_link, questions_found, connect_request)`; `failed_jobs(id, job_id, job_link, resume_tried, date_listed, date_tried, assumed_reason, stack_trace, external_job_link, screenshot_name)`; `hr_emails(id, email, job_id, title, company, job_link, email_subject, status: new|emailed, found_at, emailed_at, UNIQUE(email, job_id))`; `unanswered_questions(id, label, question_type, options JSONB, job_id, seen_count, first_seen, last_seen, UNIQUE(label, question_type))`; `linkedin_session(id=1, state: logged_in|logged_out|unknown, checked_at)`.
- Auth: `POST /api/auth/login {password}` → sets signed HTTP-only cookie (Starlette `SessionMiddleware`, `SESSION_SECRET`), constant-time compare with `UI_PASSWORD`; `POST /api/auth/logout`; `GET /api/auth/check` → 204 or 401 (used by nginx `auth_request`). Dependency `require_auth` on all routers except auth + `GET /api/health`.
- Settings API: `GET /api/settings/schema` → list of Field dicts; `GET /api/settings` → `{section: values}` (defaults merged); `PUT /api/settings/{section}` body = values → validated, saved, returns saved values; `GET /api/settings/secrets` → `[{name, env_var, set: bool}]`.

- [ ] Tests: `test_requires_login` (GET /api/settings → 401), `test_login_wrong_password_401`, `test_login_then_access`, `test_auth_check_endpoint`, `test_put_then_get_roundtrip`, `test_invalid_setting_rejected_nothing_saved` (PUT questions `{"desired_salary": "abc"}` → 422, body names `desired_salary`, GET unchanged), `test_secrets_endpoint_never_returns_values` (env has `CLAUDE_API_KEY=sk-test`; response contains no `sk-test`).
- [ ] `alembic upgrade head` on empty DB succeeds; tests pass.

### Task 4: Seed from `config/*.py` and CSVs

**Files:**
- Create: `backend/app/seed.py` (`python -m app.seed --source /legacy [--env-file /legacy-env/.env] [--write-env]`)
- Test: `backend/tests/app/test_seed.py` with fixture dir `backend/tests/app/fixtures/legacy/` (small fake `config/*.py`, fake CSVs incl. a duplicate Job ID row, a row missing columns, a latin-1 byte)

**Interfaces:**
- `parse_config_file(path: Path) -> dict[str, Any]` — `ast.parse`, collect top-level `Name = <literal>` via `ast.literal_eval` (handles `120_000`, tuples-in-parens, triple-quoted strings); non-literals skipped.
- `seed_settings(session, source: Path) -> dict[str, int]` — maps parsed values onto SCHEMA sections (secrets.py non-secret keys → `ai`), drops removed/unknown keys, validates, upserts.
- `seed_history(session, source: Path) -> SeedReport(applied, failed, emails, skipped_rows: int)` — imports `all excels/all_applied_applications_history.csv` → `applied_jobs` (upsert by job_id), `all_failed_applications_history.csv` → `failed_jobs` (skip exact duplicates), `email_apply_jobs.csv` → `hr_emails` status `new`. Read with `errors="replace"`.
- `copy_resume(source: Path, data_dir: Path) -> bool` — copies `all resumes/default/resume.pdf` if present.
- `secrets_to_env(source: Path, env_file: Path, write: bool) -> list[str]` — names from `config/secrets.py` whose env var is unset/empty in env_file; appends `KEY=value` lines only when `write`. Never prints values.

- [ ] Tests: `test_parse_config_file_literals` (`desired_salary == 120000`, `search_terms` list, multi-line `linkedin_summary`), `test_seed_settings_maps_sections` (`ai_provider` ends in section `ai`; `llm_model` dropped), `test_seed_is_idempotent` (run twice → same row counts), `test_seed_skips_bad_rows` (report.skipped_rows == 1, duplicate not doubled), `test_secrets_to_env_writes_missing_only` (existing `GLM_API_KEY` untouched; output list has names only).

**Milestone 1 handoff to Tester:** none in browser yet; Developer reports `make test` output to Maestro.

---

## Milestone 2 — Worker, bot bridge, Docker, Makefile

### Task 5: Bot control + runs/logs API

**Files:**
- Create: `backend/app/api/{bot.py,runs.py}`
- Test: `backend/tests/app/test_bot_api.py`

**Interfaces:**
- `POST /api/bot/start` → sets `bot_control.desired=running`; creates a `queued` run only if no run is `queued|running|waiting|stopping` (row lock `SELECT ... FOR UPDATE` on bot_control); returns run. `POST /api/bot/stop` → desired `stopped`.
- `GET /api/bot/status` → `{state: "idle"|"queued"|"running"|"waiting"|"stopping", run: Run|null, prompt: {id,title,text,buttons}|null, linkedin_session: {state, checked_at}}`.
- `POST /api/bot/prompts/{id}/answer {button: str}` → 409 if already answered, 422 if button not in buttons.
- `GET /api/runs?page&page_size` ; `GET /api/runs/{id}/logs?after_id=` (JSON) ; `GET /api/runs/{id}/logs/stream` (SSE, `id:` = log id, resumes from `Last-Event-ID`).

- [ ] Tests: `test_start_twice_creates_one_run`, `test_stop_sets_desired_stopped`, `test_status_includes_open_prompt`, `test_answer_prompt_validates_button`, `test_logs_after_id_pagination`.

### Task 6: Worker supervisor + UI bridge in the bot

**Files:**
- Create: `backend/app/worker.py` (`python -m app.worker`), `backend/bot/modules/bridge.py`
- Modify: `backend/bot/modules/helpers.py` (`safe_alert`, `safe_confirm` delegate to bridge when `APPLIER_DATABASE_URL` is set)
- Test: `backend/tests/app/test_worker.py` (uses a fake bot script `backend/tests/app/fakes/fake_bot.py` instead of the real bot), `backend/tests/bot/test_bridge.py`

**Interfaces:**
- `Worker.tick() -> None` — reconciles: if a `queued` run and no child → write snapshot `DATA_DIR/run/run-<id>.json` (from `settings` + defaults), spawn `[python, -u, runAiBot.py]` cwd `bot/`, env adds `APPLIER_CONFIG_FILE`, `APPLIER_DATABASE_URL`, `APPLIER_RUN_ID`, `DISPLAY`; mark `running`. If `desired=stopped` and child alive → mark `stopping`, SIGTERM, SIGKILL after 5 s, mark `stopped`, close open prompts (answer=`"__stopped__"`). If child exits → `finished` (code 0) or `failed` (error = last 20 log lines). Stdout lines → `run_logs` (batched every 0.5 s). `Worker.run_forever(poll=1.0)`.
- `bridge.ask(title: str, text: str, buttons: list[str]) -> str` — inserts prompt, sets run `waiting`, polls every 1 s, returns the answer; on `"__stopped__"` raises `SystemExit(0)`; sets run back to `running`.
- `bridge.record_session(state: str)`, `bridge.record_unanswered(label, question_type, options, job_id)`, `bridge.save_applied(row: dict)`, `bridge.save_failed(row: dict)`, `bridge.save_emails(job: dict, emails: list[str], subject: str)`, `bridge.applied_job_ids() -> set[str]`, `bridge.bump_counts(applied=0, failed=0, skipped=0)`.

- [ ] Tests: `test_queued_run_starts_child_and_captures_logs`, `test_snapshot_contains_saved_settings_not_secrets`, `test_crashing_bot_marks_run_failed` (fake bot exits 1 → `failed`, error has its last line, worker idle), `test_stop_while_waiting_closes_prompt` (fake bot calls `bridge.ask`; desired=stopped → exits ≤5 s, prompt answered `__stopped__`), `test_bridge_ask_returns_answer`.

### Task 7: Bot wired to DB; removals; Chrome for container

**Files:**
- Modify: `backend/bot/runAiBot.py`, `backend/bot/modules/open_chrome.py`, `backend/bot/modules/validator.py`, `backend/bot/modules/helpers.py`
- Delete: `backend/bot/modules/ai/{openaiConnections,deepseekConnections,geminiConnections}.py`, `backend/bot/modules/resumes/generator.py`, `app.py`, `templates/`, `applications_viewer.html`, `setup/`, `requirements*.txt` (replaced by pyproject)
- Test: `backend/tests/bot/test_bot_wiring.py`

Changes: `submitted_jobs`, `failed_job`, `email_apply_job` (removed), `get_applied_job_ids` use `bridge` instead of CSV; counts via `bridge.bump_counts`; drop sponsor popup in `main()`, `keep_screen_awake`, ChatGPT-tab/resume-generator code, non-Claude/GLM provider branches; validator drops removed settings. `open_chrome.createChromeSession`: when `CHROME_BINARY` / `CHROMEDRIVER` env set, pass `browser_executable_path` / `driver_executable_path` to `uc.Chrome` and `version_main` from `chromium --version`; `--user-data-dir=$CHROME_PROFILE_DIR` (default `/data/chrome-profile`), `--no-sandbox`, `--disable-dev-shm-usage`. After login check, `bridge.record_session("logged_in"|"logged_out")`. Login captcha/2FA wait in `login_LN` goes through `pyautogui.alert` → bridge ("Finish LinkedIn login in the live browser, then click Done", button `"Done, continue"`).

- [ ] Tests: `test_removed_modules_gone` (import of `modules.ai.openaiConnections` fails), `test_applied_ids_come_from_bridge` (monkeypatched bridge), `test_validator_accepts_defaults`.
- [ ] `pytest tests -q` all pass; `grep -rn "pyautogui.alert(\"Please consider sponsoring" backend` → nothing.

### Task 8: Docker images, compose, nginx, Makefile

**Files:**
- Create: `docker/compose.yaml`, `docker/stack/{api,worker,frontend}.Dockerfile`, `docker/stack/worker-entrypoint.sh` (Xvfb `:99` 1920x1080x24, fluxbox, x11vnc `-forever -shared -nopw -localhost`, websockify+noVNC on 6080, then `python -m app.worker`), `docker/stack/nginx.conf`, `.env.example`, `Makefile`, `.dockerignore`
- Modify: `.gitignore` (add `.env`, `backups/`)

Compose: `postgres:16` (volume `pgdata`, healthcheck), `api` (runs `alembic upgrade head` then uvicorn :8000), `worker` (volume `data` at `/data`, `shm_size: 2gb`, env `CHROME_BINARY=/usr/bin/chromium`, `CHROMEDRIVER=/usr/bin/chromedriver`), `frontend` (nginx; `ports: ["127.0.0.1:8080:80"]`). api and worker get secrets via `env_file: ../.env`. nginx: `/` SPA fallback; `/api/` → `api:8000`; `/novnc/` → `worker:6080` with websocket upgrade and `auth_request /api/auth/check`.
Makefile: `up` (create `.env` from example if missing, generating `SESSION_SECRET` with `openssl rand -hex 32`; then `docker compose -f docker/compose.yaml up -d --build`; print URL `http://localhost:8080`), `down`, `logs`, `test` (backend pytest in api container against `TEST_DATABASE_URL` on the postgres service + `npm test` in frontend image stage), `seed` (`docker compose run --rm -v $(PWD):/legacy:ro -v $(PWD)/.env:/legacy-env/.env api python -m app.seed --source /legacy --env-file /legacy-env/.env --write-env`), `migrate`, `shell-api`, `shell-worker`, `shell-db`, `backup` (`pg_dump` → `backups/<timestamp>.sql`), `restore FILE=...`.

- [ ] From a fresh clone in `/tmp/applier-clean`: `make up` → all 4 services healthy; `curl -s localhost:8080/api/health` → `{"ok":true}`; `make test` green.

**Milestone 2 handoff to Tester:** `make up` from a clean clone; `http://localhost:8080/novnc/vnc.html` and `/api/settings` return 401 without login, and after `POST /api/auth/login` noVNC shows the worker desktop; `make seed` imports settings + history (row counts match the CSVs) and lists missing secrets without printing values; start a run via `POST /api/bot/start` and see Chromium open in noVNC; `make test` green.

---

## Milestone 3 — Bot fixes and email collection

### Task 9: Email extraction + collection rule

**Files:**
- Create: `backend/bot/modules/emails.py`
- Modify: `backend/bot/runAiBot.py` (AI screen block ~line 1570)
- Test: `backend/tests/bot/test_emails.py`

**Interfaces:**
- `extract_emails(text: str) -> list[str]` — lowercase, order-preserving dedupe, strips trailing `.,;:)>]`, ignores asset-like matches ending in `.png|.jpg|.jpeg|.gif|.svg|.webp`.
- `should_collect_emails(ai_filter_jobs: bool, match_score: int | None, min_score: int) -> bool` — `False` only when `ai_filter_jobs and match_score is not None and min_score > 0 and match_score < min_score`.
- Bot: after the AI screen (or when AI is off/failed), if `should_collect_emails(...)`, merge `extract_emails(description)` with AI `apply_email` and call `bridge.save_emails(job, emails, relevance.get("email_subject",""))`.

- [ ] Tests: `test_extract_emails_basic` (`"Send CV to Jobs@Acme.com." → ["jobs@acme.com"]`), `test_extract_emails_dedup_and_assets` (`"a@b.io a@b.io logo@2x.png" → ["a@b.io"]`), `test_should_collect` table: `(False,None,50)→True`, `(True,None,50)→True`, `(True,40,0)→True`, `(True,60,50)→True`, `(True,40,50)→False`.

### Task 10: Fix "Follow company" checkbox

**Files:**
- Create fixture: `backend/tests/bot/fixtures/easy_apply_review.html` (captured from a real "Review your application" step, PII replaced, then **discard** the application)
- Modify: `backend/bot/modules/linkedin_ui.py` (add `FOLLOW_COMPANY_CHECKBOX_XPATH`, `FOLLOW_COMPANY_LABEL_XPATH`), `backend/bot/runAiBot.py:follow_company`
- Test: `backend/tests/bot/test_linkedin_ui.py`

- [ ] Root-cause with systematic-debugging on the captured page (why `input#follow-company-checkbox` misses).
- [ ] Tests: `test_follow_checkbox_found_on_review_page` (XPath finds exactly one checkbox input, its label text contains `"to stay up to date"`), `test_follow_label_clickable_target`.
- [ ] `follow_company` uses the new XPaths, clicks the label when `is_selected() != follow_companies`, re-reads state and logs if it's still wrong; called immediately before clicking Submit.

### Task 11: Fix filters (job type, remote, country, Easy Apply)

**Files:**
- Create fixture(s): `backend/tests/bot/fixtures/search_results_filtered.html` (real results page loaded with the configured URL)
- Modify: `backend/bot/modules/helpers.py` (`build_jobs_search_url`), `backend/bot/modules/linkedin_ui.py`, `backend/bot/runAiBot.py:apply_filters`
- Test: `backend/tests/bot/test_search_url.py`, `backend/tests/bot/test_filters.py`

**Interfaces:**
- `read_applied_filters(page) -> dict[str, Any]` — reads LinkedIn's filter pills/state from the results page: keys `job_type: list[str]`, `on_site: list[str]`, `location: str`, `easy_apply: bool`.
- `missing_filters(expected: dict, applied: dict) -> list[str]` — names of expected filters not applied.
- `apply_filters()` (bot): after load, `missing = missing_filters(...)`; re-apply each missing one through the page UI (or fix URL params, e.g. `geoId` for country, whatever root cause shows); re-check once; still missing → `print_lg` + `bridge.ask("Filters not applied", "<list>. Fix them in the live browser, then continue.", ["Done, continue"])` when `pause_after_filters`, else log.

- [ ] Root-cause with systematic-debugging: load the URL from `build_jobs_search_url` for the owner's config in the worker Chrome, see which params LinkedIn drops/rewrites (`f_JT`, `f_WT`, `location`, `f_AL`).
- [ ] Tests: `test_read_applied_filters_from_fixture`, `test_missing_filters_detects_each` (expected `{job_type:["Contract","Temporary"], on_site:["Remote"], location:"United States", easy_apply:True}` vs applied missing each one → each name returned), plus a URL test pinning whatever param fix the root cause needs.

### Task 12: Custom answers + unanswered questions + session status

**Files:**
- Modify: `backend/bot/runAiBot.py:answer_questions`, `backend/bot/modules/helpers.py`
- Create: `backend/app/api/questions.py`
- Test: `backend/tests/bot/test_custom_answers.py`, `backend/tests/app/test_questions_api.py`

**Interfaces:**
- `lookup_custom_answer(label: str, custom_answers: list[dict]) -> str | None` — case-insensitive substring `match` in label; first match wins; checked before built-in/AI answers for text, textarea, select, radio.
- Bot records every question it couldn't answer via `bridge.record_unanswered` (upsert, `seen_count+1`).
- API: `GET /api/questions/unanswered?page&page_size&q`; `POST /api/questions/unanswered/{id}/answer {answer}` → appends `{match: label, answer}` to `questions.custom_answers`, deletes the row.

- [ ] Tests: `test_lookup_custom_answer` (`[{"match":"German","answer":"None"}]` + `"Proficiency in german?" → "None"`; no match → None), `test_answer_unanswered_moves_to_custom_answers`.

**Milestone 3 handoff to Tester:** settings change used by next run (change `search_terms` to one term, start, confirm logs show it); follow checkbox unticked on review step (Developer's discard run); filters applied on results page in noVNC; emails captured.

---

## Milestone 4 — History, emails API, CSV export

### Task 13: History, HR emails, export API

**Files:**
- Create: `backend/app/api/{history.py,emails.py,export.py}`, `backend/app/compose_email.py`
- Test: `backend/tests/app/{test_history_api.py,test_emails_api.py,test_compose_email.py,test_export.py}`

**Interfaces:**
- `GET /api/history/applied` and `/failed`: `?q&company&date_from&date_to&page=1&page_size=25` → `{items, total, page, page_size}`, newest first.
- `GET /api/emails`: `?status=new|emailed&company&role&date_from&date_to&q&page&page_size` → same envelope.
- `GET /api/emails/{id}/compose` → `{to, subject, body_text, body_html}`; `POST /api/emails/{id}/mark-emailed` → status `emailed`, `emailed_at=now`; `POST /api/emails/{id}/mark-new`.
- `compose(email_row, email_settings) -> Composed` — substitutes `{hr_email}`, `{job_title}`, `{job_url}`, `{my_name}`; `[text](url)` → `<a href="url">text</a>` in HTML (HTML-escaped otherwise, newlines → `<br>`), and `text (url)` in plain text.
- `GET /api/export/{applied|failed|emails}.csv` — streams CSV with the original column headers.

- [ ] Tests: `test_compose_matches_spec_example` (job title "Senior Full Stack Software Engineer", url `https://www.linkedin.com/jobs/view/1` → subject `"Senior Full Stack Software Engineer - Jane Doe"`, html contains `<a href="https://www.linkedin.com/jobs/view/1">Senior Full Stack Software Engineer</a>` and `linkedin.com/in/janedoe`), `test_compose_escapes_html` (title `<b>x</b>` escaped), `test_email_filters_and_pagination` (30 rows → page 2 of size 25 has 5; `status=emailed` filters), `test_mark_emailed_sets_timestamp`, `test_export_applied_headers`.

---

## Milestone 5 — Frontend

All pages: loading, empty, error states; keyboard focus, labels, contrast; responsive down to 1280 px wide desktop (mobile not required). Vitest tests per page for key behaviour with mocked fetch.

### Task 14: Scaffold, login, layout, API client

**Files:** `frontend/` (Vite React TS), `src/api/client.ts` (fetch wrapper, `credentials: "include"`, 401 → redirect `/login`), `src/pages/Login.tsx`, `src/components/Layout.tsx` (nav: Dashboard, Settings, History, Emails, Questions)
- [ ] Tests: `Login shows error on 401`, `redirects to dashboard after login`.

### Task 15: Dashboard — bot control, live view, needs-you, logs

**Files:** `src/pages/Dashboard.tsx`, `src/components/{BotControls,LiveBrowser,NeedsYouBanner,LogStream,SessionBadge}.tsx`
- LiveBrowser: iframe `/novnc/vnc.html?autoconnect=1&resize=scale&path=novnc/websockify`.
- Status polled every 2 s (react-query). When state becomes `waiting`: banner with prompt title/text and one button per `buttons` → `POST answer`; fire `Notification` (ask permission on first Start).
- LogStream: EventSource on current run; auto-scroll with "pause scroll" toggle; last 2000 lines kept.
- [ ] Tests: `Start disabled while running`, `banner renders prompt buttons and posts answer`, `log lines append from stream`.

### Task 16: Settings

**Files:** `src/pages/Settings.tsx`, `src/components/settings/{FieldInput,SectionForm,AnswersEditor,SecretsPanel,ResumeUpload}.tsx`, backend `POST /api/resume` (PDF/DOC/DOCX ≤ 2 MB → `DATA_DIR/resumes/default/resume.pdf`, add to Task 13 files) and `GET /api/resume` (metadata)
- Form generated from `/api/settings/schema`; one tab per section; per-field inline 422 errors; "Saved — used on next run" toast. Email section shows live preview via the compose rules (call `/api/emails/preview` with sample values — add endpoint in Task 13 `emails.py`: `POST /api/emails/preview {subject_template, body_template, my_name}` → Composed for a sample job).
- SecretsPanel: list from `/api/settings/secrets`, "set / not set", note "edit `.env` and run `make up`".
- [ ] Tests: `renders enum as select with schema options`, `shows field error from 422`, `secrets panel never shows values`.

### Task 17: History, Emails, Questions pages

**Files:** `src/pages/{History,Emails,Questions}.tsx`, `src/components/{DataTable,Pagination,FilterBar,CopyEmailModal,ConfirmSentDialog}.tsx`
- Emails: filters status/company/role/date/search, pagination; per row "copy address" icon button and **Copy** → `CopyEmailModal` shows To / Subject / Body exactly as composed, each with its own copy button; body copies with `ClipboardItem` (`text/html` + `text/plain`). On close → `ConfirmSentDialog` "Did you send it?" Yes → `mark-emailed`; No → nothing.
- History: tabs Applied / Failed, filters + pagination, links to job, "Export CSV".
- Questions: unanswered list with inline answer input → POST.
- [ ] Tests: `copy modal shows composed email`, `confirm yes marks emailed and refreshes list`, `confirm no leaves status new`, `filters update query string and refetch`, `pagination moves pages`.

**Milestone 5 handoff to Tester:** full UI pass per page; login wall incl. direct `/novnc/` and `/api/*` without cookie → 401.

---

## Milestone 6 — Docs and end-to-end

### Task 18: README + clean-clone run

- [ ] Rewrite `README.md`: prerequisites (Docker Desktop), `make up`, `.env` secrets, `make seed`, using noVNC for captcha/2FA, backup/restore.
- [ ] In `/tmp/applier-clean` (fresh `git clone` + copy of working tree changes): `make up && make seed && make test` succeed.

### Task 19: Tester end-to-end (real LinkedIn apply)

- [ ] Tester: login UI → edit a setting → Start → watch in noVNC (owner handles captcha/2FA if asked via Maestro) → at least one real Easy Apply submitted, "Follow" unticked at review, filters correct on results page, applied row visible in History, any found HR emails in Emails with working Copy flow.
- [ ] Done when Tester's last report is all PASS and `make test` is green.

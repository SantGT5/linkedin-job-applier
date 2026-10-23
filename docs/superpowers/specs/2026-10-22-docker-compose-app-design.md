# LinkedIn auto-apply bot → Docker Compose app — Design

Date: 2026-10-22 · Status: approved 2026-10-22 (all ADD and REMOVE items approved)

## Intent

Today the bot is a set of Python scripts configured by editing `config/*.py`, with history in CSV files and a small Flask viewer (`app.py`, `templates/`, `applications_viewer.html`). The owner wants one local app, started with `make up`, where they:

- edit every bot setting in a web UI instead of Python files,
- start/stop the bot, watch it work (live Chrome view + live logs), and step in when it gets stuck,
- browse application history,
- collect HR email addresses from job descriptions and send follow-up emails themselves with one click to copy.

Local-only, single user.

## Goals

1. `make up` from a clean clone starts everything (frontend, api, worker, postgres).
2. Every setting from `config/*.py` is editable in the UI and used by the **next** bot run.
3. The worker runs Chrome (undetected-chromedriver + PyAutoGUI) inside Xvfb and exposes noVNC, embedded in the UI, so the owner can watch and intervene (captcha, 2FA, unanswered questions).
4. Secrets are never stored in plain text in the DB or shown in the UI.
5. A seed script imports the current `config/*.py` values (and existing CSV history) into the DB.
6. All existing tests keep passing (moved/refactored as needed).
7. UI is behind a password.
8. New: HR email list (below).
9. Fix: search filters not fully applied; "Follow <company>" checkbox not unticked before submit.

## Non-goals

- Multi-user, hosting, or exposure beyond localhost.
- The app sending email itself (explicitly rejected by the owner).
- Rewriting the bot's apply logic beyond what the refactor and the two fixes need.

## Anti-goals (failure even if it "works")

- Editing a setting in the UI that the bot silently ignores.
- A run that blocks on a popup nobody can see.
- Secrets visible in the UI, API responses, logs or the DB in plain text.
- Breaking the existing tests or the bot's current apply behaviour.

## Constraints

- Stack (owner's decision): `frontend/` React + Vite + TypeScript; `backend/` Python with two services from one codebase (`api`, `worker`); `postgres`; `docker/compose.yaml`, `docker/stack/*.Dockerfile`; `Makefile` with `up, down, logs, test, seed, migrate, shell-*`.
- Bot keeps undetected-chromedriver + PyAutoGUI.
- Bind all published ports to `127.0.0.1`.

## Decided by the owner

### HR email list

- **Collect:** the bot still applies to the job as normal. In addition, for jobs that **passed the AI match score**, every email address in the description is saved with job id, title, company, job link, date found. (Jobs that fail the score: no emails saved.) "Passed" includes every case where the bot applies without a real score: AI filter off, AI disabled, AI call failed/no score, or threshold 0. Those jobs are applied to and their emails saved. Only a real score below the threshold excludes a job.
- **List page:** paginated table; filters for status (new / emailed), company, role, date found, plus free-text search.
- **Copy, not send.** Each row has:
  - a small button that copies just the address;
  - a **Copy** button that opens a modal showing the composed email:

    ```
    email to: <hr_email>
    title: <job_title> - <my_name>

    Hi,

    Hope this message finds you well.

    I came across the [<job_title>](<job_url>) role and I'd love to be considered,

    I've attached my CV for your review,

    Thank you for your time,

    Best regards,
    <my_name>
    <phone_number>
    <linkedin_profile>
    ```

  - When the modal closes, it asks "Did you send it?". **Yes** → row marked emailed (with timestamp). **No** → unchanged; Copy can be used again.
- No multi-select / bulk send.

### Bot stuck → owner fills it in

When the bot meets something it can't handle (unanswered question, captcha/2FA, "pause before submit", "pause after search"), it **pauses** instead of showing a desktop popup. The UI shows a "Bot needs you" banner (plus a browser notification) with the live Chrome view; the owner fixes it in Chrome via noVNC, clicks **Done, continue**, and the bot carries on.

### Bug fixes

- **Filters:** the search filters are frequently not all applied, so the owner fixes them by hand every run. The ones that go missing: **job type**, **remote (on-site/remote/hybrid)**, **country (search location)**, and sometimes **Easy Apply**. Fix it.
- **Follow company:** on the "Review your application" step the "Follow <Company> to stay up to date with their page" checkbox stays ticked. `follow_company()` (`runAiBot.py:1142`) looks for `input#follow-company-checkbox`, which LinkedIn no longer renders that way, and fails silently. It must be unticked (per the `follow_companies` setting) before **Submit application**.

## Claude's calls (owner can override)

- **Secrets: keep them in `.env`** (recommended over encrypt-at-rest). Local single-user app: encrypting in the DB still needs a master key, which would live in `.env` anyway, so it adds complexity without adding protection. Secrets covered: LinkedIn username/password, all AI API keys, UI password, session signing key. The UI's Settings shows each secret as "set / not set" (never the value) with a note to edit `.env`. `.env` is git-ignored; `.env.example` is committed.
- **UI auth:** one password (`UI_PASSWORD` in `.env`), signed HTTP-only session cookie, all API routes require it except login and health.
- **How config reaches the bot:** the bot keeps its `from config.X import *` style. Bot code moves into `backend/` and its `config` package becomes thin loaders that read a JSON snapshot (path from env) and fall back to safe defaults when absent (so tests run without a DB). For each run the worker reads settings from postgres + secrets from env, writes the snapshot, and launches the bot as a **fresh subprocess**; stop = terminate the subprocess. This is what makes "edits apply to the next run" true and keeps the bot's import-time Chrome start working.
- **Bot ↔ UI pause/continue:** replace the blocking `pyautogui.alert/confirm` pauses with a helper that writes a "waiting for user" state (reason + message) to the DB and polls until the API marks it resolved. Non-interactive alerts become log lines.
- **Logs:** worker captures bot stdout/stderr per run into postgres; API streams them to the UI (SSE). Runs table keeps start/end/status/counters.
- **Seed:** `make seed` reads top-level `config/*.py` **by parsing (AST), not importing**, upserts settings into the DB, imports the three CSVs in `all excels/` (applied, failed, email-apply) into history tables, and copies the default resume into the resume volume. It prints which secrets from `config/secrets.py` are missing from `.env` (and offers to append them) rather than storing them in the DB. Re-running seed is idempotent.
- **Email extraction:** regex over the description (free, deterministic), deduped per job; the AI relevance call's existing `apply_email`/`email_subject` is merged in. Same address on different jobs = separate rows.
- **Email template:** editable in Settings with placeholders `{hr_email}`, `{job_title}`, `{job_url}`, `{my_name}`, defaulting to the text above. Body copies as rich text (HTML + plain-text fallback) so links survive pasting into Gmail.
- **Filter fix approach:** after the results page loads, read back what LinkedIn actually applied and compare with config; re-apply what's missing through the page UI, and log/show in the UI any filter that still can't be applied. Root cause investigated with captured real pages (systematic-debugging), regression tests with HTML fixtures.
- **Follow fix approach:** find the checkbox by its label text ("Follow … to stay up to date") within the modal, set it to `follow_companies` right before clicking Submit, with a fixture-based test from a captured review page.
- **Old email-apply log is folded into the HR list:** `ai_log_email_apply` and `email_apply_jobs.csv` go away; seed imports the existing CSV rows into the HR email list with status "new".
- **Worker browser on Apple Silicon:** native arm64 Chromium (with its matching chromedriver) driven by undetected-chromedriver, not amd64 Chrome under emulation, which is slow and flaky.
- **Live LinkedIn while building:** the owner asked for a real apply, so Developer and Tester use the owner's real account via noVNC. Developer captures real pages (results page, review step) for fixtures and discards before submitting; only Tester's end-to-end run submits a real application.
- **Persistence:** postgres data, Chrome profile (keeps LinkedIn logged in), resumes, logs/screenshots each on named volumes.
- **Tests:** existing `tests/` move to `backend/tests/bot/` unchanged in intent; `make test` runs backend pytest (in the container) and frontend tests.

## Left to the builder

Web framework, ORM/migrations tool, DB schema, API shape, frontend libraries, styling, page layout, how settings are grouped in the UI, Xvfb/noVNC images, exact Makefile recipes.

## Feature changes — all APPROVED by the owner

ADD
1. **Unanswered-questions list** — log questions the bot couldn't answer so you can add answers in Settings and it stops pausing on them.
2. **CSV export** of history and emails — keeps the spreadsheet workflow you have today.
3. **LinkedIn session status** on the dashboard — you see "logged out" before starting a run, not after it fails.
4. **`make backup` / restore** of postgres — history now lives in the DB, not loose CSVs.

REMOVE
1. **`app.py`, `templates/`, `applications_viewer.html`** — replaced by the new frontend + api.
2. **Startup "sponsor" popup** — blocks every run until clicked.
3. **`keep_screen_awake`** — meaningless inside a container.
4. **`setup/` scripts (sh/bat/ps1)** — replaced by Docker + `make up`.
5. **Commented-out ChatGPT-tab and resume-generator code** (`use_resume_generator`, `modules/resumes/generator.py`) — marked "In Development", never runs.
6. **OpenAI / DeepSeek / Gemini providers** — job screening and email extraction only work with Claude and GLM; dropping the rest removes ~700 lines and settings you don't use.

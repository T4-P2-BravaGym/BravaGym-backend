# HU-35 Password Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver private, single-use password recovery and sign out every old session after success.

**Architecture:** FastAPI routes validate and delegate to reset services; a background delivery adapter owns an injected session factory and EmailSender. SQLite transactions consume the reset token, change the password and increment a per-user session version together. React uses the existing public layout, UI components, HTTP client and Vitest setup.

**Tech Stack:** Existing FastAPI, SQLAlchemy/Alembic, bcrypt, pytest/freezegun; React JavaScript, SASS Modules, Vitest/Testing Library. No new dependencies.

**Spec:** `specs/HU-35-password-reset.md` in the backend repository, shared with frontend.

## Global Constraints

- Work in feature/hu-35-password-reset branches based on current origin/dev; preserve existing changes. No pushes to dev, no merges.
- Spec copy: generic 202 detail `Si existe una cuenta activa con ese email, recibirás un enlace para recuperar tu contraseña.`
- Invalid reset 400 detail `El enlace no es válido o ha caducado. Solicita uno nuevo.`
- Opaque `secrets.token_urlsafe(32)`, SHA-256 storage, UTC lifetime exactly 30 minutes, three deliveries per normalized email per fifteen minutes.
- Password minimum eight characters, maximum 72 UTF-8 bytes; no automatic login.
- Outbox private 0700 directory/0600 files, ignored by Git and not HTTP-served. No emails, tokens, passwords, hashes or links in logs or validation responses.
- UI Spanish; code/comments/commits English; spec and shared AI log follow Spanish repository convention.
- Preserve existing tests; no skips or relaxed expectations to pass the suite. Vitest only for frontend.
- User approved invalidating all old access/refresh sessions. No real SMTP delivery or optional email verification.

## Review Focus

- Missing/malformed legacy JWT `ver`: accept absent only as version zero, reject bool/string/negative; reset blocks legacy tokens.
- Background delivery and DB failures: same generic response, independent session lifecycle, no secrets in logs and no password changes.
- Unicode password byte limits and malformed JSON/extra fields: safe 422 responses with no echoed secrets; token remains usable.
- Fragment handling under React StrictMode/reload: retain token in memory through rerenders, remove URL fragment without losing it on effect replay; clear it after success.
- Confirmation/reset races with refresh: old sessions cannot survive a committed reset; consume/reset and refresh updates must check current account version atomically.

## Task 1: Reset storage and session-version enforcement

**Files:** backend `app/models/password_reset.py` (new), `app/models/user.py`, `app/models/__init__.py`, new migration after current Alembic head; `app/core/security.py`, `app/core/deps.py`, `app/services/auth_service.py`; model/security/session unit and integration tests.

**Interfaces:** `PasswordResetToken(id, user_id, token_hash, created_at, expires_at, used_at)`; `User.session_version` int default/server_default 0. `create_access_token(user_id, role, session_version=0)` and `create_refresh_token(user_id, role, session_version=0)` emit `ver`; decoder validates present versions and maps absent to 0. Existing two-argument test helpers remain valid for accounts at version 0.

- [ ] Write failing tests for model hash-only fields, unique hash/FK, migration/model parity, JWT version cases and old access/refresh/logout rejection when user version changes. Preserve and extend allowed-claims assertions with `ver`.
- [ ] Run focused pytest; record failures demonstrating missing model/version behavior.
- [ ] Implement model and additive reversible migration, exact current head obtained with Alembic. Enforce account version in current-user dependency, refresh conditional UPDATE and logout ownership checks. Issue sessions with actual user version. Reset is not implemented here.
- [ ] Run targeted model/security/auth/session tests and migration upgrade/check/downgrade/upgrade on temporary SQLite; existing login/refresh/logout behavior must remain green.
- [ ] Commit `feat(auth): add reset token storage and session versions`.

## Task 2: Generic reset request and private development delivery

**Files:** new backend `app/core/email.py`, `app/core/password_reset_delivery.py`, `app/services/password_reset_service.py`, `app/schemas/password_reset.py`, `app/routers/password_reset.py`; `app/main.py`, config, rate limiter, .env.example/.gitignore; request/email/config tests.

**Interfaces:** `EmailSender` Protocol: `send(*, recipient: str, subject: str, body: str) -> None`; `OutboxEmailSender(directory: Path)` implements it with random filenames and exclusive creation. `request_password_reset(db: Session, email: str, sender: EmailSender, frontend_url: str) -> None` generates/stores token for an active current user and sends via injected sender. `deliver_password_reset(email, session_factory, sender, frontend_url)` is an infrastructure task using its own injected session context and catches errors with generic safe logging. Routes enqueue this job using BackgroundTasks and dependency-injected factory/sender, so unknown/active/delivery-failure paths return the same 202. No request DB session is retained by a background task.

- [ ] Write failing tests: known/unknown/inactive generic202, zero plaintext tokens in DB/responses/logs, normalization, outbox file modes/name/contents, unknown no delivery, configured trusted frontend URL rather than Host, delivery/DB failure safe202, repeated delivery suppression after three requests. Tests use temporary directories and injected factory for the test DB.
- [ ] Write failing safe422 tests for bad email, malformed body and extra fields containing a token/password. Limit email255, token1..256; reject extras. Use a router-scoped validation route class/handler that emits safe loc/type/message only, never input/context/body; preserve safe client-readable detail format.
- [ ] Run focused tests; implement sender, validated frontend origin (localhost5173 default only local), background adapter, service, generic no-store response and router registration. Outbox adapter must fail closed outside local when no real sender configured; no SMTP dependencies.
- [ ] Use three-per-email/fifteen-minute in-memory delivery limiter, key hashed normalized email, injectable/resettable for tests. Rate limiting changes deliveries, never the generic202. Reset endpoints never expose token through JWT/cookie or redirect bodies.
- [ ] Run focused request/outbox/config tests and existing auth tests. Verify git ignores generated outbox files.
- [ ] Commit `feat(auth): add private password recovery requests`.

## Task 3: Atomic reset confirmation and global session invalidation

**Files:** backend reset service/schemas/router from Task2; reset confirmation/security/concurrency tests.

**Interfaces:** `confirm_password_reset(db: Session, token: str, new_password: str) -> None`; POST `/api/v1/auth/password-reset/confirm` body `{token,new_password}`, public, 204/no body. Shared invalid-reset AppError400; safe validation422. Never use access/refresh authentication dependencies for recovery.

- [ ] Write failing tests: new-password login succeeds/old fails; bad/used/mutated/unknown/inactive tokens400; 29:59 accepted/30:00 rejected with freezegun; bad password422 without consumption; UTF-8 bcrypt limit; other outstanding reset links invalidated; audit updated_at/updated_by_id recorded for recovered user.
- [ ] Add failure/rollback and two-real-connection SQLite concurrency tests proving exactly one confirmation succeeds and no partial password/token/version update. Test all preexisting access/refresh rejected, including legacy tokens with no ver, while new login works. Race reset against refresh: no old session remains valid after reset commit.
- [ ] Implement conditional token consumption with account-active check in one transaction; bcrypt-hash new password; atomic increment of current user version, revoke all existing refresh and consume sibling reset tokens; rollback every change on failure. Use current DB version, never stale ORM value for concurrent increments. Safe success logging with user_id only, no-store204.
- [ ] Run all reset tests plus existing auth/session/password-change tests; full backend pytest, lint/format and migration parity. Do not change unrelated password-change semantics.
- [ ] Commit `feat(auth): confirm password resets and revoke old sessions`.

## Task 4: Recovery pages and Vitest coverage

**Files:** frontend `src/services/auth.js`, `src/routes/paths.js`, `src/routes/AppRouter.jsx`, login link; new `src/pages/public/ForgotPassword/` and `ResetPassword/` with pages, styles, index exports and colocated tests. Reuse existing Field/Button/Alert/PublicLayout minimal.

**Interfaces:** `requestPasswordReset(email)` POST `/auth/password-reset` `{email}`; `confirmPasswordReset(token,newPassword)` POST `/auth/password-reset/confirm` `{token,new_password:newPassword}`; both `auth:false`. PATHS `forgotPassword:'/recuperar-contrasena'`, `resetPassword:'/nueva-contrasena'`. Link `<frontend>/nueva-contrasena#token=<opaque token>`.

- [ ] Read existing Sandbox component entries before adding page UI; use existing components, so no new reusable UI/catalog entry required.
- [ ] Write failing service tests verifying endpoint, JSON body and no auth-refresh attempt. Write Testing Library tests for request generic success, duplicate-click/loading, network retry, email validation and login navigation.
- [ ] Write failing reset-page tests for missing token, fragment parsing/removal, StrictMode/rerenders, byte/length validation, mismatch, invalid/expired token400 with new-link CTA, network retry preserving memory token, success clearing form/token and internal login link. Confirm token never reaches storage or API URL.
- [ ] Implement pages with noValidate forms, labels, disabled duplicate submit, password reveal/repeat, accessible Alert states, no automatic login. Read token through lazy state; remove fragment using replaceState while preserving unrelated query/path, avoid effect-replay token loss. Full reload after removal shows new-link CTA.
- [ ] Use SASS modules and design tokens for all new values; reuse existing typography mixins. Add only link to login. No external analytics or redirects.
- [ ] Run `npm test`, `npm run lint`, `npm run build`; preserve all current67 tests plus new cases.
- [ ] Commit `feat(auth): add password recovery pages`.

## Task 5: Integration, documentation and final review

**Files:** backend shared spec/AI log/README/API docs/config examples; frontend README; review screenshots in frontend docs/screenshots if UI changed.

- [ ] Exercise real local flow against disposable SQLite/outbox: unknown email generic202, known private link, new password204, reused400, old/new login, old access/refresh rejected. No demo passwords/token contents in shared artifacts. Do not alter the user's normal DB.
- [ ] Browser checks both pages: keyboard/focus, visible error/loading/success, 320/375px without overflow; capture screenshots with fictional data, never reset token in browser chrome/artifact.
- [ ] Document local outbox workflow, configured frontend URL, 30-minute lifetime, legacy ver0 compatibility, full-session invalidation, non-durable background work, delivery throttling, and production EmailSender requirement. Record exact AI help, errors and evidence in shared log.
- [ ] Run full backend pytest with coverage>=80, Ruff checks, migration upgrade/check/downgrade/upgrade on temporary DB and pip-audit. Run full frontend Vitest, lint, build and npm audit. Inspect staged diffs for secrets and scope.
- [ ] Request independent whole-branch code/security review against this spec and plan; fix findings with regression tests and rerun affected/full checks.
- [ ] Commit documentation; verify clean working trees. Only after all work passes: push feature branches, prepare/open PRs to dev according to user's instruction, monitor CI and report concrete review links. Never self-approve or merge.

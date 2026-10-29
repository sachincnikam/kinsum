# Kinsum — project guide for Claude

**Kinsum: family money, added up.** A private, local-first personal and household finance app.
It imports bank, credit-card and investment statements (CSV and PDF, layout differs per
institution), categorizes transactions, and gives monthly insights, budgets, goals and a
net-worth view for any number of family members.

Full product and build plan: `docs/plan.md`. Read it before starting a new feature.

## Non-negotiable privacy rules

1. **Real statements never enter the repo.** The owner only has real statements. Never copy,
   move, read into a test, or commit a real statement file. `.gitignore` blocks
   pdf/csv/xls/xlsx/ofx/qfx/qbo/txt everywhere; only `sample-data/**/*.fake.*` is allowed.
   Never weaken these rules, and never use `git add -f` on such files.
2. **Test data is fake.** Fixtures live in `sample-data/<bank>/<name>.fake.csv|pdf`, copy only
   the *layout* of a real statement, and use invented names, numbers and amounts.
3. **No account details or account-holder names are ever sent to AI.** That covers names,
   account numbers, addresses and balances tied to a person.
4. **User data lives outside the repo**, in `%LOCALAPPDATA%\Kinsum` (platformdirs). That covers
   the database, backups, learned layouts, logs and the AI audit log. Secrets live in `.env`
   (git-ignored); the template is `.env.example`.
5. The server binds to **127.0.0.1 only**.

## AI usage policy: three jobs only

AI (the Anthropic API, key in `.env`) may be used **only** for:

1. **Categorizing merchants never seen before.** Send only the cleaned merchant/description
   text and amount sign, never account or person data. The result is remembered in
   `merchants`, so each merchant is asked about once.
2. **Learning a new PDF layout once**, from a **redacted** sample. Crop the page header and
   footer, scrub names, account numbers and addresses, and use an allow-list of fields.
   **If redaction is in doubt, block the call.** Save the learned layout locally and parse
   that layout with code from then on.
3. **Ask Kinsum (Phase 5).** Turn a plain-English question into **read-only SQL** that runs
   locally. Family member names are replaced with placeholders before sending. Optional
   AI-written summaries see totals only and are **off by default**.

Every AI call is written to a local audit log. With no API key, the app must still work
(manual categorization, manual layout mapping).

## Tech stack

- **Backend:** Python 3.13, FastAPI, uvicorn, SQLAlchemy, pydantic-settings, platformdirs.
  SQLCipher-encrypted SQLite (`sqlcipher3-wheels`) and `cryptography` for the key file.
  Tests use pytest + httpx.
- **Frontend:** React 19, Vite 7, TypeScript, Tailwind v4 (`@tailwindcss/vite`), with IBM Plex
  Sans/Mono from @fontsource so it works offline.
- In dev, Vite proxies `/api` to port 8000. In "prod", FastAPI serves `frontend/dist` with an
  SPA fallback.
- **Platform:** Windows laptop first, Mac later, hosting maybe later. USD only. Six months of
  history to start. Investments use statement values (no live prices).

## Commands (Windows, run from the repo root)

| Task | Command |
| --- | --- |
| One-time setup | `.\setup.bat` |
| Run the app (http://localhost:8000) | `.\start.bat` |
| Dev mode (backend reload + Vite at http://localhost:5173) | `.\dev.bat` |
| Backend tests | `cd backend; .venv\Scripts\python -m pytest -q` |
| Frontend build / type check | `cd frontend; npm run build` |

CI (`.github/workflows/tests.yml`) runs the backend tests and the frontend build on Windows and macOS.

## Repo layout

```
backend/app/        FastAPI app: config.py (settings, data dir), main.py (create_app, SPA serving),
                    vault.py (key file), db.py (encrypted database + migrate), lock.py (app lock,
                    sessions, get_me/require_household), models.py (tables), household.py (routes)
backend/migrations/ Alembic, hand-written revisions in versions/ (run on every unlock)
backend/tests/      pytest (fixtures in conftest: fresh app per test in tmp_path, fake clock)
frontend/src/       React app: api.ts (fetch + types), App.tsx (lock state, who is signed in),
                    pages/ (Household, Settings), components/ (LockScreen, Modal, Sidebar, …),
                    lib/money.ts (cents <-> text)
docs/plan.md        product and build plan
sample-data/        FAKE statements only (*.fake.*)
```

## App lock and encryption (Phase 1 step 2)

- Data folder holds `kinsum.db` (SQLCipher, raw 256-bit key) and `vault.json`. The vault has one
  slot per passcode: the database key wrapped with AES-256-GCM under an scrypt-derived key. No
  names or data in it. Losing `vault.json` means losing the database.
- **Recovery key:** one more slot (`kind: "recovery"`) holding a printable 25-character key
  (Crockford base32, 5 groups of 5). It is shown at setup and must be confirmed as saved; it
  resets a forgotten passcode on the lock screen and is replaced right after use; Settings can
  make a new one (needs the passcode). Passcode and recovery guesses share one wrong-try counter.
- Each adult who signs in has their own passcode slot; `members.slot_id` links them. A session
  remembers its slot, so the app knows who is signed in (`get_me`). Two adults can't share a
  passcode (unlocking couldn't tell them apart). Changing a passcode or making a recovery key
  needs your *own* passcode. Recovery with several adults answers 409 with `choices` (names),
  then takes `member_id`. A step-2 passcode with no member gets a one-time "What's your name?".
- Every `/api` route needs the session cookie unless listed in `lock.PUBLIC_PATHS`, so new routes
  are locked by default. Data routes take `db: Session = Depends(get_db)` (423 when locked).
- Locking (button, idle timeout `KINSUM_IDLE_LOCK_MINUTES` default 10, or quitting) forgets the
  key, closes the database and ends every session. `/api/lock/status` never counts as activity.
- After 5 wrong passcodes the wait doubles from 30 s up to 15 min. Only `Host: localhost` or
  `127.0.0.1` is accepted (blocks DNS rebinding); tests use `base_url="http://localhost"`.
- Tables come from Alembic migrations (`backend/migrations/versions`, written by hand, no
  autogenerate) applied by `Database` on every open. Add a new revision for every table change.
- The engine must keep `poolclass=QueuePool`: with the placeholder URL `sqlite://` SQLAlchemy would
  pick `SingletonThreadPool`, which crashed the whole app on parallel requests.

## Household (Phase 1 step 3)

- Members: name, colour (fixed palette), role adult/teen/child, archived flag. Only adults sign in.
- Access for adults who sign in: `household` (everything, and manages members, sign-ins and the
  recovery key) or `own` (only accounts they own, alone or shared; can add and edit those, must
  stay an owner). At least one signed-in adult with `household` access always remains.
- Accounts: bank's name, institution, optional nickname (shown everywhere via `display_name`),
  `last4` only (the API refuses anything but exactly 4 digits; the form keeps the last 4 of a
  pasted number), type, opening balance in cents, opening date, one or more owners. Balances are
  from the household's view: credit cards and loans store what is owed as negative; the form asks
  for "amount owed". Accounts and members are archived, never deleted.

## Data model (16 tables, planned)

members · accounts (nickname, last4) · account_owners (shared accounts allowed) · imports ·
import_events · transactions (spent_by_member_id, merchant_id) · categories (icon, colour) ·
tags + transaction_tags · rules · recurring · budgets · balances/holdings · merchants ·
saved_reports · savings_goals · alerts

**Duplicate-proof import**, checked in this order:

1. Same file (hash)
2. Same statement (account + period + closing balance)
3. Overlapping transactions

The statements folder is optional; upload works without it. Every import, skip and undo is
written to `import_events`, which feeds the import activity log.

## UI

- **Top-right icons:** Import statements · Ask Kinsum · Inbox (with count badge).
- **Sidebar (12 items):**

| Group | Items |
| --- | --- |
| (top) | Dashboard · Transactions (Grid/Calendar toggle) · Recurring & subscriptions |
| Insights | Monthly review · Month to month · Merchants · Net worth & look back |
| Plan | Budgets & limits · Savings goals |
| Setup | Categories, tags & rules · Household & accounts · Settings |

  Plus "Lock app" at the bottom.

- **Light design tokens:** page `#F1F5F9`, primary `#1E40AF`, income `#047857`, over/negative
  `#B91C1C`, muted `#475569`. Amounts use the `.amount` class (mono, tabular figures). The
  tokens are defined in `frontend/src/index.css` (`@theme`).
- **Logo:** concept A, "Growing family": three rising figures on a blue rounded square, the
  tallest in green `#34D399`. Wordmark "kin" + green "sum". File: `frontend/public/kinsum.svg`.
- Accessibility: visible focus rings, `prefers-reduced-motion` respected, and colour is never
  the only signal.

## Roadmap

- **Phase 1 Foundation (current):**
  1. Repo and Windows launcher ✅ (starter)
  2. Passcode, app lock and encrypted DB ✅
  3. Members and accounts (owners, shared accounts, nicknames) ✅
  4. Categories with icons
  5. CSV/PDF import with per-bank layouts
  6. Duplicate and transfer detection
- **Phase 2 Organize:** rules, merchant memory, AI for new merchants, tags and bulk edit,
  "spent by", review inbox, statements folder with import log and undo.
- **Phase 3 Understand:** dashboard, month to month, merchant analysis, why-is-this-month-different,
  unusual charge alerts, monthly family review, calendar, balance sheet, point-in-time look back.
- **Phase 4 Plan ahead:** recurring and upcoming items, safe to spend, budgets and alerts,
  savings goals, subscription audit, fees and interest watch, merchant limits, month-end review,
  splits, encrypted backup/restore, installers (.exe via GitHub Releases, .dmg later).
- **Phase 5:** Ask Kinsum.

## How to get statement layouts without real data

- **CSV:** the owner pastes only the header row and the bank name. Claude writes a matching
  `*.fake.csv` fixture.
- **PDF:** build a small local tool that prints a statement's structure with every name,
  number and amount masked (e.g. `Date | Description | XXXX.XX`). The owner reviews it and
  shares only that output. Claude writes the fake fixture from it.

## Open decisions

- Idle auto-lock time: 10 minutes by default, set with `KINSUM_IDLE_LOCK_MINUTES` in `.env`.
- Member picker (filter every screen by member or group) waits for Phase 3, when there is data
  to filter.
- Moving between computers uses an encrypted backup file. There is no sync between two laptops.

## Working conventions

- Keep the plan and code in step. If a feature changes, update `docs/plan.md` too.
- Add or update tests with every backend change; keep `npm run build` passing.
- Prefer small, reviewable commits with clear messages.
- Explain steps in plain language. The owner is comfortable with VS Code but is not a
  full-time developer.

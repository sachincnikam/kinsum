# Kinsum

**Family money, added up.** A private, local app that turns bank, credit-card and investment
statements into one categorized ledger, monthly insights, budgets, goals and a net-worth view —
for any number of family members. Everything runs on your own laptop.

- Plan: [`docs/plan.md`](docs/plan.md)
- Status: **Phase 1 · Foundation — starter version**

## First-time setup (Windows)

You need **Git**, **Python 3.13** and **Node.js (LTS)** installed.

1. Open this folder in VS Code.
2. Open a terminal (**Terminal → New Terminal**) and run:

   ```
   .\setup.bat
   ```

   This creates the Python environment, installs packages, builds the screens,
   creates your `.env` settings file and runs the tests.

## Running Kinsum

```
.\start.bat
```

The browser opens at <http://localhost:8000>. Only this computer can connect.
Close the window to stop Kinsum.

### Development mode

```
.\dev.bat
```

Opens the app at <http://localhost:5173>; screens update as soon as code changes.

## Where things live

| What | Where |
| --- | --- |
| Code | this repo (`backend/` FastAPI, `frontend/` React + Tailwind) |
| Your data (database, backups, logs) | `%LOCALAPPDATA%\Kinsum` — never in the repo |
| Settings and AI key | `.env` (ignored by git); template in `.env.example` |
| Fake statements for tests | `sample-data/` |

## Privacy rules for this repo

- Never commit `.env`, databases, backups or real statements (`.gitignore` blocks them).
- Keep GitHub secret scanning and push protection turned on.
- Tests use fake data only.

## Tests

```
cd backend
.venv\Scripts\python -m pytest
```

GitHub Actions runs the tests on Windows and Mac for every push.

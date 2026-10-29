# Kinsum — Product & Build Plan

Copy of the live plan document ("Kinsum — Product & Build Plan" in Claude Docs), saved for project reference; last updated Oct 21, 2026. The live doc is the source of truth; refresh this copy when the plan changes.

## Vision and goals

One private app that turns statements from every bank, credit card and brokerage into a single, categorized ledger, a monthly spending picture, a living budget and a net-worth balance sheet.

**Goals**

1. **Import anything** — upload CSV, OFX/QFX, PDF or Excel statements from any institution without manual retyping.
2. **Categorize automatically, correct easily** — smart auto-categories, with full control to add categories and re-categorize any transaction.
3. **Explain the why with tags** — optional free-form tags (e.g. `vacation-2026`, `wedding`, `car-repair`) so an unusual month can be traced to its reason.
4. **Compare months** — clear month-to-month and year-over-year views of income, spending and savings.
5. **Budget that adapts** — suggested budgets from history, editable by you, with alerts and progress tracking.
6. **Know your net worth** — a balance sheet of assets (cash, investments) and liabilities (credit cards, loans) over time.

**Non-goals for v1:** live bank sync (Plaid etc.), bill pay, tax filing, live investment prices, internet hosting (planned for later). These can come later.

## Core features

Twenty-two must-have features cover everything you asked for, including the thirteen you added; four more round it out later, including Ask Kinsum.

| Feature | What it does | Priority |
| --- | --- | --- |
| Household members | Shared on your computer behind an app passcode. Add any number of family members (adults, teens, children) and change them any time. Each account belongs to one member or is shared by several, and a purchase on a shared account can be credited to whoever made it. Every screen filters by one member, a group, or the whole household. Each adult can have their own passcode. | Must (v1) |
| Accounts | Add accounts by institution and type (checking, savings, credit card, brokerage, retirement, loan), with owner and opening balance. Give any account an optional nickname (e.g. "Grocery card", "Kids' college fund"); it is shown everywhere in place of the bank's name, with the bank name and last 4 digits underneath. Rename any time. | Must (v1) |
| Statement upload | Upload CSV or PDF (Excel/OFX also accepted). Auto-detect the institution, map columns once per institution, preview, then import. Duplicate detection across overlapping statements. | Must (v1) |
| Auto-categorization | Assign a category to every transaction using your rules, merchant memory, keywords and an optional AI fallback. Shows a confidence level. | Must (v1) |
| Custom categories | Two-level hierarchy (e.g. Food > Groceries). Add, rename, merge, archive. Each has an icon, picked from a searchable icon library, and a colour; starter categories come with icons. Mark as income, expense, transfer or investment. | Must (v1) |
| Re-categorize | Change any transaction's category inline or in bulk. Offer to "apply to all similar" and create a rule so it sticks next time. | Must (v1) |
| Tags | Optional, multiple per transaction. Free-form with autocomplete. Filter, report and compare by tag. Bulk-tag a date range or search result. | Must (v1) |
| Month-to-month analysis | Income vs expense, savings rate, category and tag breakdowns, change vs last month and vs 3/6/12-month average, top movers, "why is this month different". | Must (v1) |
| Budgets | Fixed monthly amounts per category, suggested from history. Edit, roll over unspent amounts, track progress, alert at 80% and 100%. | Must (v1) |
| **Point-in-time view** (new) | Pick any past date: see each account's balance on that day, total cash and net worth, and income and expense month-to-date and year-to-date as of that date. | Must (v1) |
| **Calendar** (new) | Monthly calendar with daily income/expense totals on each day. Select a date to list its transactions; future days show expected recurring items. | Must (v1) |
| **Recurring detection** (new) | Find repeating income and expenses (salary, rent, subscriptions, bills) with their usual amount, frequency and next expected date. Flag new, missed or price-changed ones. | Must (v1) |
| **Upcoming on dashboard** (new) | Next 30 days of expected income and expenses from recurring items, with projected balance per account and a low-balance warning. | Must (v1) |
| **Merchant analysis** (new) | Spending per merchant for any month or date range: total, visits, average purchase, share of spending and change vs last month and 6-month average. Merchant detail with trend and transactions; insights on top merchants, biggest movers, new merchants and visit frequency; optional monthly limit per merchant. | Must (v1) |
| **Statements folder** (new) | Optional folder the app scans for new statements; read-only, works alongside upload, never required. Same-file, same-statement and overlapping-transaction checks stop duplicates from either source. | Must (v1) |
| **Import activity log** (new) | Every upload and folder event with time, source, file, account, who and result (imported, skipped as duplicate and why, waiting, failed). Filter, open the import, export to CSV. | Must (v1) |
| **Unusual charge alerts** (new) | Flag charges far above normal for a merchant, big charges from new merchants, possible double charges and creeping bills. | Must (v1) · Phase 3 |
| **Monthly family review** (new) | Automatic one-page monthly summary: what changed and why, goals, bills ahead, things to check. PDF export. | Must (v1) · Phase 3 |
| **Savings goals** (new) | Target amount and date, progress, monthly amount needed; linked to an account or tag. | Must (v1) · Phase 4 |
| **Subscription audit** (new) | Yearly cost of every subscription; duplicates, price rises, trials ending, unused ones. | Must (v1) · Phase 4 |
| **Safe to spend** (new) | What is left this month after upcoming bills and goal contributions; 3-month balance forecast. | Must (v1) · Phase 4 |
| **Fees and interest watch** (new) | Year-to-date bank fees, late fees, foreign-transaction fees and card interest; alert on new ones. | Must (v1) · Phase 4 |
| **Ask Kinsum** (new) | Ask questions or request reports in plain English; the AI writes a read-only query, Kinsum runs it locally and shows a table or chart. Save answers as reports; export CSV/PDF. Your data never leaves the laptop. | Phase 5 |
| Balance sheet | Assets, liabilities and net worth per month from statement ending balances (investments at statement value). Trend over time. | Should (v2) |
| Split transactions | Split one charge across categories (e.g. a Costco run = groceries + household). | Should (v2) |
| Export & backup | Export to CSV/Excel, full encrypted backup and restore. | Should (v2) |

**Transfers and card payments** are detected and excluded from spending, so paying your credit card from checking is not counted twice.

## Data model

Sixteen core tables hold everything; transactions sit at the centre, linked to an account, a category, an import batch and any number of tags.

| Table | Key fields | Notes |
| --- | --- | --- |
| `members` | id, name, colour, role, slot_id, access, is_archived | Any number of family members; adults can have their own passcode (a slot in the key file, so `slot_id` set = can sign in) and access level (whole household, or own and shared accounts), children can be tracked without signing in |
| `accounts` | id, name, nickname, institution, last4, type, currency (USD), opening_balance, opening_date, is_active | Owners are listed in account_owners: one member, or several for a shared account. Type: checking, savings, credit_card, brokerage, retirement, loan |
| `imports` | id, account_id, source (upload or folder), uploaded_by, file_name, file_hash, statement_key, format, period_start, period_end, closing_balance, row_count, rows_skipped, stored_copy, imported_at | One per imported statement; lets you undo a whole import |
| `transactions` | id, account_id, import_id, date, description_raw, merchant_clean, amount, direction, category_id, notes, is_transfer, transfer_pair_id, recurring_id, spent_by_member_id, dedupe_hash, categorized_by | `categorized_by` = rule, memory, ai or manual |
| `categories` | id, name, parent_id, kind, icon, colour, is_archived | Kind: income, expense, transfer, investment |
| `tags` + `transaction_tags` | tag id, name, colour; join table of transaction_id and tag_id | Many-to-many; a transaction can carry several tags |
| `rules` | id, match_field, match_type, pattern, amount_min, amount_max, account_id, set_category_id, set_tags, priority | Created manually or from "apply to similar" |
| `recurring` | id, account_id, merchant, category_id, kind, typical_amount, amount_tolerance, frequency, day_of_month, next_expected_date, status | Kind: income or expense. Status: active, paused, ended. Confirmed or dismissed by you |
| `budgets` | id, category_id, month, amount, rollover, source | Fixed monthly amount; source = suggested or manual |
| `balances` / `holdings` | account_id, as_of_date, balance; account_id, as_of_date, symbol, quantity, statement_value | Statement ending balances anchor the point-in-time view and balance sheet |
| `merchants` | id, display_name, match_patterns, default_category_id, monthly_limit | Groups raw bank descriptions into one merchant; transactions link to it by merchant_id |
| `account_owners` | account_id, member_id | Links each account to one or more members; a shared account simply has several rows |
| `import_events` | id, time, source, file_name, file_hash, event, member_id, import_id, matched_import_id, message | The import activity log; the statements folder path is a per-computer setting, not stored here |
| `saved_reports` | id, title, question, query, chart_type, created_by, created_at, last_run_at | Ask Kinsum answers saved as reports; rerun locally without the AI |
| `savings_goals` | id, name, target_amount, target_date, account_id, tag_id, monthly_contribution, owner_member_id, status | Feeds the goals progress and safe-to-spend number |
| `alerts` | id, kind, transaction_id, merchant_id, recurring_id, message, created_at, status | Unusual charges, double charges, creeping bills, new fees, trials ending; dismissed or resolved by you |

**Rules for money:** store amounts as integer cents (never floats), keep the raw description untouched, and keep every edit reversible.

## Statement import pipeline

Every upload passes through the same seven steps, and nothing is saved until you confirm the preview.

1. **Upload** — drag in one or many files; pick the account (or let the app suggest it from the file).
2. **Detect format** — CSV, OFX/QFX, XLSX or PDF. Match against saved "institution profiles" by headers and layout.
3. **Parse**
   - CSV/Excel: column mapping (date, description, amount or debit/credit, balance). Saved per institution so you map once.
   - OFX/QFX: accepted if a bank offers it later; not required since your banks provide CSV and PDF.
   - PDF: text extraction with per-bank templates; for a new layout, AI learns the layout once from a redacted sample, then a saved template parses that bank's PDFs locally from then on. Scanned PDFs use OCR.
4. **Normalize** — one date format, signed amounts (credit card sign conventions flipped correctly), clean merchant names (strip store numbers, "POS", "SQ *").
5. **De-duplicate** — hash of account + date + amount + normalized description; fuzzy match within ±3 days for overlapping statements. Flag, don't silently drop.
6. **Categorize & detect transfers** — run the categorization engine; pair matching debits/credits between your own accounts as transfers.
7. **Preview & confirm** — table of new, duplicate and low-confidence rows; fix categories here, then commit. The whole import can be undone later.

**Investment statements** also capture ending balance and holdings (symbol, quantity, statement value) for the balance sheet; buys, sells, dividends and fees become transactions with investment categories.

### Statements folder (optional) and duplicate-proof import

You can point the app at one folder of statements; it picks up new files from there, and uploading still works the same. The folder is a convenience only — the app never depends on it.

**How the folder works**

- **Choose it in Settings** (for example `Documents\Statements`, subfolders included), or leave it unset.
- **When it scans:** at start-up, every few minutes while the app is open, and on **Scan now**. It waits until a download has finished and ignores temporary files.
- **Read-only:** the app never moves, renames or deletes your files.
- **Same path as uploads:** a new file goes through the same steps as an upload. If the bank layout and account are already known, it imports automatically and shows a summary; anything that needs a decision (new layout, unknown account, password-protected PDF) waits in the Review inbox.

**No dependency on the folder**

- **Everything needed lives in the app's encrypted database:** the transactions, a fingerprint of every statement ever imported, and (setting on by default) an encrypted copy of each original statement. All of it is in the backup.
- **Deleting or moving files in the folder changes nothing** in the app; the log simply notes a file is gone.
- **Folder missing or unplugged** (e.g. a USB drive) → the app shows "folder not available" and carries on; upload still works.
- **Moving to another laptop:** the folder setting belongs to each computer, so after restoring a backup the app asks you to choose a folder again (or skip). If you point it at a copy of the same folder, every old file is recognized and skipped — nothing is imported twice.
- **Tip:** a folder in OneDrive works on any laptop you sign in to; the app still treats it as optional.

**Duplicate detection — the same rules for folder and upload**

| Check | Catches | Result |
| --- | --- | --- |
| 1. Same file | Exactly the same file again, even renamed or uploaded after the folder already took it | Skipped; log names the earlier import |
| 2. Same statement | The same statement in another format or a re-download (same account and same period, matching closing balance) — e.g. the CSV after the PDF | Skipped; log explains which statement it matches |
| 3. Overlapping transactions | Statements whose dates overlap (e.g. a mid-month download, then the full month) | Only new transactions are added; repeats are skipped and counted in the log |

**Import activity log** — every event is recorded with time, source (upload or folder), file name, account, who (member or "folder watcher"), and result: found, imported (rows, period), skipped as duplicate (and why), waiting for review, failed (reason), file removed from folder, folder unavailable, import undone. You can filter it by source, result, account and date, open the import behind any line, and export it to CSV. The log is in the backup, so it moves with your data.

## Categorization engine

Categories are assigned by a four-layer cascade, and every manual correction teaches the first two layers so accuracy improves each month.

1. **Your rules** (highest priority) — e.g. description contains "SHELL" → Transportation > Fuel; amount between $1,800 and $1,900 from checking on the 1st → Housing > Rent. Rules can also add tags.
2. **Merchant memory** — the category you last chose for this cleaned merchant name.
3. **Built-in keyword/MCC map** — a starter dictionary (Amazon, Uber, Netflix, Walmart…) plus card-network merchant category codes when present.
4. **AI fallback (optional)** — used only when layers 1–3 have never seen the merchant. Sends the cleaned description, amount and date (nothing else) to an LLM, which picks a category from *your* category list. The answer is saved to merchant memory, so the same merchant never goes to AI twice. Can be switched off entirely.

Anything still uncertain lands in **Uncategorized** and shows in a "Needs review" inbox.

**When you change a category**, the app asks: *just this one*, *all past transactions from this merchant*, or *all past and future* (creates a rule). The same choice applies to tags.

**Starter categories** (fully editable):

| Group | Example sub-categories |
| --- | --- |
| Income | Salary, Bonus, Interest, Dividends, Refunds, Other income |
| Housing | Rent/Mortgage, Utilities, Internet & phone, Maintenance, Home insurance |
| Food | Groceries, Restaurants, Coffee, Delivery |
| Transportation | Fuel, Car payment, Car insurance, Parking & tolls, Rideshare, Transit |
| Shopping | Clothing, Electronics, Household, Online marketplaces |
| Health | Medical, Pharmacy, Fitness, Health insurance |
| Lifestyle | Entertainment, Subscriptions, Travel, Gifts, Personal care |
| Family & education | Childcare, School, Pets |
| Financial | Fees & interest, Taxes, Charity |
| Investments (investment kind) | Buy, Sell, Investment fees |
| Transfers (excluded from spend) | Card payment, Between accounts, Investment contribution |

**Category icons** — every category shows its icon on a small tile tinted with its colour, wherever the category appears: transaction rows, the edit sheet, budgets, the dashboard, the calendar's day list and the comparison table. Icons come from an open-source line-icon set (for example Lucide) bundled with the app, so they work offline. When you create or edit a category you pick an icon from a grid, search it by word ("pet", "gym", "rent"), and choose a colour from a palette; you can change either at any time. Uploading your own icon images is left for later.

## Analysis and budgeting

The analysis answers three questions each month — where did money go, how does it compare, and why is it different — and the budget turns those answers into next month's plan.

**Month-to-month reports**

- **Summary cards:** income, spending, net savings, savings rate, net worth — each with change vs last month.
- **Category comparison:** this month vs last month vs 3-, 6- and 12-month average, with dollar and percent change. Sorted by biggest movers.
- **Trend charts:** 12-month income vs expense bars; stacked spending by category; savings-rate line.
- **Tag analysis:** total by tag per month, and "spending without tagged one-offs" so a vacation month doesn't distort your baseline.
- **"Why is this month different?"** — automatic explanation: lists categories more than 25% (or a dollar threshold you set) above average, plus the tags and largest transactions that drove them. Example: *Travel up 1,420 USD vs average — 92% tagged `hawaii-2026`.*
- **Drill-down:** click any number to see the transactions behind it; filter by account, category, tag, merchant, amount, date.

**Budget setup and updates**

1. **Suggest** — for each expense category, propose the median of the last 3–6 months, excluding transactions with one-off tags. Fixed bills (rent, subscriptions) use the latest amount.
2. **Review** — you accept, edit or zero out each line; add an overall savings goal.
3. **Track** — progress bars per category, pace indicator ("62% spent, 50% of month gone"), alerts at 80% and 100%.
4. **Roll over (optional)** — unspent or overspent amounts carry into next month per category.
5. **Re-tune monthly** — at month end, a review screen shows budget vs actual and suggests adjustments for categories consistently over or under by more than 10%. You approve changes; nothing updates silently.

**Balance sheet** — assets (cash + investment market value) minus liabilities (card balances + loans) = net worth, recorded each month from statement ending balances, with a trend line and breakdown by account.

**Point-in-time view** — the balance on any past date is rebuilt from the nearest statement ending balance, then rolled forward or back by the transactions in between. Income and expense as of that date are month-to-date and year-to-date sums up to it. Where no statement balance exists, the app works from the opening balance and flags the result as estimated.

**Recurring detection** — group transactions by cleaned merchant and account, then look for a steady interval (weekly, every two weeks, monthly, quarterly, yearly) at least three times, with amounts within about 10%. Each match becomes a suggested recurring item with typical amount, usual day and next expected date. You confirm, edit or dismiss it; new imports are matched automatically and flagged when a payment is missed, early, late or changes price.

**Upcoming income and expenses** — confirmed recurring items are projected forward 30 days (adjustable). The dashboard lists them by date and projects each account's balance day by day, warning when a checking account would dip below a threshold you set.

**Calendar** — a month grid showing total income and expense on each day, coloured by net. Tapping a past day lists its transactions (editable in place); tapping a future day lists the expected recurring items.

**Merchant analysis** — merchant names are cleaned and grouped, so "AMZN Mktp US*2K4", "Amazon.com" and "AMZN Digital" all count as Amazon; you can rename, merge or split merchants, and the grouping is remembered. For each merchant the app shows:

- **Totals for the period** — amount spent, number of visits, average purchase, share of total spending, and change vs last month and vs the 6-month average.
- **Merchant detail** — 6-month trend, all its transactions, split by owner and card, and the tags used.
- **Insights** — top merchants, biggest movers, merchants new this month, visit-frequency changes (e.g. 18 coffee visits vs 11 usual), and possible double charges (same merchant, same amount, same day).
- **Merchant limits (optional)** — set a monthly limit on any merchant (e.g. Amazon 400 USD) and get the same 80% and 100% alerts as budgets.

The "Why is this month different?" card also names the merchants that drove each change.

### Planning and alert extras

Six additions reuse the recurring, budget and merchant work, so they cost little to build.

| Feature | What it does | Phase |
| --- | --- | --- |
| **Unusual charge alerts** | Flags a charge far above the usual amount for that merchant, a large charge from a new merchant, a possible double charge, and bills creeping up (e.g. electric up 18% on last year). Shown on the dashboard and in the Review inbox. | 3 |
| **Monthly family review** | An automatic one-page summary each month, made on the laptop: what changed and why, goals progress, bills ahead, and things to check. Opens in the app and exports to PDF for a family money talk. | 3 |
| **Savings goals** | Goals such as "Hawaii 2027" or "Emergency fund": target amount and date, progress, and "save $X a month to get there". Linked to an account, a tag, or both. | 4 |
| **Subscription audit** | Every subscription with its yearly cost; flags duplicates, price rises, free trials about to turn into charges, and ones with no recent use. | 4 |
| **Safe to spend** | One number on the dashboard: what is left this month after upcoming bills and savings-goal contributions, plus a 3-month balance forecast. | 4 |
| **Fees and interest watch** | Year-to-date totals of bank fees, late fees, foreign-transaction fees and card interest (e.g. "$186 in fees this year"), with an alert when a new one appears. | 4 |

### Ask Kinsum (questions and reports in plain English)

Type a question or ask for a report — "Compare dining spend per family member over the last 6 months", "Which subscriptions went up this year?" — and get a table or chart built from your own data. **The AI writes the query; your laptop finds the answer**, so transactions never leave the app.

**How it works**

1. **You ask** in plain English on the Ask Kinsum screen.
2. **Kinsum sends Claude only** your question (with family names swapped for placeholders such as "Member 1"), a description of the tables (names and columns) and your category names. No transactions, amounts, balances or account details are sent.
3. **Claude returns a database query** (an exact instruction such as "sum Dining by member by month").
4. **Kinsum checks and runs it locally** against your encrypted data, then shows the result as a table or chart, with export to CSV or PDF.

**Safeguards**

- **Read-only:** the query runs on a read-only connection, may only read the approved tables, and is rejected if it tries to change anything. Results are capped in size and time.
- **Shows its reading of your question** — e.g. "Dining · May–Oct 2026 · all members · by month" — with **Show how** to see the query. If it misunderstood, you rephrase or adjust the filters directly.
- **Save as report:** a useful answer becomes a saved report you can rerun any month; saved reports run locally without the AI.
- **Logged:** every question and what was sent appear in the AI log.
- **Written summaries (optional, off by default):** a short explanation in words needs the AI to see the summarised result (totals only, never individual transactions or account details). Turned on separately in Settings.
- **Fully offline later:** a small AI model running on the laptop could replace Claude for this feature, so even the question stays local — weaker on hard questions and needs a capable laptop.

## Screens

Sixteen screens cover the app, reached from a left sidebar on laptop and bottom tabs on phone; a member picker (everyone, one member or any group) sits at the top of every screen.

**Menu: 12 sidebar items grouped by what you are doing, plus 3 quick-action icons at the top right:**

| Group | Items |
| --- | --- |
| Top-right icons (every screen) | Import statements · Ask Kinsum · Inbox (with a count of to-dos and alerts) |
| Top | Dashboard · Transactions (grid or calendar view) · Recurring & subscriptions |
| Insights | Monthly review · Month to month · Merchants · Net worth & look back |
| Plan | Budgets & limits · Savings goals |
| Setup | Categories, tags & rules · Household & accounts · Settings |

| Screen | Main contents |
| --- | --- |
| Dashboard | Month picker; summary cards; **upcoming income and expenses (next 30 days) with projected balance**; spending by category donut; income vs expense trend; budget progress; "why this month is different" card; needs-review count; safe-to-spend number; unusual-charge alerts; fees and interest this year |
| Calendar (new) | Calendar view of the Transactions screen (Grid / Calendar toggle): month grid with daily income/expense totals; select a date to see its transactions, or expected items for future dates |
| As-of view (new) | Date picker; balances per account, total cash, net worth, and month-to-date / year-to-date income and expense as of that date |
| Transactions | Searchable, filterable table (incl. owner); inline category dropdown and tag chips; multi-select for bulk re-categorize / tag / delete; split and note actions |
| Recurring (new) | Detected and confirmed recurring items: amount, frequency, next date, last paid; confirm, edit, pause or dismiss; alerts for missed or changed amounts; subscription audit (yearly cost, duplicates, price rises, trials ending, unused) |
| Import | Drop zone; import history with undo; column-mapping wizard per institution; preview with duplicates and low-confidence rows highlighted |
| Review inbox | Inbox: uncategorized and low-confidence transactions, newly detected recurring items, and alerts (unusual charges, double charges, creeping bills, new fees); one-click accept, change or dismiss |
| Monthly comparison | Category table across months with deltas and sparklines; tag view; drill-down |
| Budgets | Setup wizard with suggested fixed amounts; per-category progress; month-end review and re-tune; savings goals with progress and monthly amount needed |
| Balance sheet | Net worth trend; assets and liabilities by account and owner; manual balance entry for accounts without statements |
| Settings | Household members, accounts and their owners, institution profiles, categories, tags, rules, AI on/off, low-balance threshold, export, backup |
| Merchants (new) | Merchant list sorted by spend, change, visits or new; insights card; merchant detail with 6-month trend, owner split, transactions, rename/merge and monthly limit |
| Household members (new) | Member cards with role, sign-in and access, accounts owned and month's spending; add, edit or archive a member; account ownership table (one member or shared) |
| Import activity (new) | Statements folder status and Scan now; log of every upload and folder event with filters, duplicate explanations, links to imports and CSV export |
| Ask Kinsum (new) | Question box with suggested questions; answer as table or chart with "how I read your question" filters and Show how; save as report, export; list of saved reports and recent questions |
| Monthly family review (new) | One-page month summary: what changed and why, goals progress, bills ahead, alerts to check; PDF export |

## Tech stack options

Decision: **Option A (local-first web app)** for now. It runs on your laptop in the browser, your financial data stays on your computer, and there is no hosting cost. Suggested stack: Python FastAPI backend with SQLite (encrypted with SQLCipher), and a React + Tailwind frontend. The database layer uses SQLAlchemy with migrations, so moving to hosted Option B later (Vercel, Supabase Postgres and Render, about 32 USD/month) is a configuration change, not a rewrite.

| Option | Stack | Pros | Cons |
| --- | --- | --- | --- |
| A. Local-first web app (chosen) | Python FastAPI or Node backend, SQLite, React + Tailwind + a chart library (Recharts/ECharts), runs on your laptop | Maximum privacy, no hosting cost, simple | Only on that computer unless you sync the DB file |
| B. Hosted web app (later) | Same app on a small server or Supabase (Postgres + auth), with login | Access from phone and any device | Must handle security, hosting cost ~5–20 USD/month |
| C. Desktop app | Tauri or Electron wrapping the same React UI + SQLite | Feels native, encrypted local file | More packaging work, no mobile |

**Key libraries regardless of option**

- Parsing: `pandas` / `papaparse` (CSV), `ofxparse` (OFX/QFX), `openpyxl` (Excel), `pdfplumber` + OCR (PDF).
- Merchant cleaning and fuzzy matching: `rapidfuzz`.
- AI categorization and PDF fallback: an LLM API (e.g. Claude), opt-in.
- Charts: Recharts or ECharts.

### GitHub repository

All code lives in one private GitHub repository; your statements, database and keys never do.

```
kinsum/
  backend/        FastAPI app, parsers, categorization engine, tests
  frontend/       React + Tailwind screens
  sample-data/    fake statements, used only by tests
  docs/           this plan and decisions
  .env.example    settings template, no real values
  .gitignore
  README.md       how to install and run locally
```

- **Never committed** (blocked in `.gitignore`): the database file, uploaded statements, backups, PDF layout samples, the `.env` file holding the AI API key, and the AI audit log.
- **Private repo** with GitHub secret scanning and push protection on, so an API key pushed by mistake is blocked.
- **Tests use fake data only** — invented sample statements per bank format, so the repo is safe even if shared.
- **One branch per phase** (e.g. `phase-1-foundation`), merged to `main` through a pull request; GitHub Actions runs the tests on every push.
- **Running it from the repo** — clone the repo, copy `.env.example` to `.env`, run one start command, open it in your browser. Your data folder sits outside the repo.
- **Family access for now** — the app runs on one laptop; each family member signs in there with their own passcode. Phone access comes with hosting later.

### Running, installing and moving the app

The app is built for **Windows first**, written so the same code runs on a Mac later without changes.

**Opening it on Windows**

- **During development:** run `start.bat` from the repo; the browser opens at `http://localhost:8000` on the passcode screen.
- **Everyday use:** a Start-menu and desktop shortcut starts the app and opens the browser. A small icon by the clock shows it is running, with **Open**, **Lock** and **Quit**.
- **Only this laptop can connect** — the app accepts no connections from other devices on the Wi-Fi.

**Installing on another machine**

| Step | Windows (now) | Mac (later) |
| --- | --- | --- |
| Installer | One `.exe` installer with Python and everything else built in | One `.dmg`, built from the same code |
| Where it comes from | Your private repo's GitHub Releases page; GitHub Actions builds it for each new version | Same page, built on a Mac runner |
| Data folder | `%LOCALAPPDATA%\Kinsum` | `~/Library/Application Support/Kinsum` |
| First-run warning | Unsigned installer shows a SmartScreen warning (More info → Run anyway); a code-signing certificate removes it | Unsigned app needs right-click → Open once; a paid Apple Developer account removes it |

**Moving your data (including Windows → Mac)**

1. Old laptop: Settings → **Export encrypted backup**.
2. Copy the file by USB stick or cloud drive — it stays encrypted.
3. New laptop: install the app → **Restore from backup** → enter the passcode. The backup file works on both Windows and Mac.

**Keeping the Mac move easy:** use only libraries that work on both systems, never hard-code Windows paths, and run the automated tests on Windows and Mac from Phase 1. Two laptops do not sync: one is the main copy, and backups move data between them until hosting is added.

### Name and logo

The app is called **Kinsum** — *kin* + *sum*, "what the family adds up to." Repo: `kinsum`; Windows data folder: `%LOCALAPPDATA%\Kinsum`.

- **Logo (chosen: concept A, "Growing family"):** three family figures of rising height on a trust-blue rounded square, which also read as a bar chart; the tallest is income green. Clear down to 16 px for the browser tab and Windows tray icon.
- **Wordmark:** "kinsum" in lowercase IBM Plex Sans SemiBold, with "sum" in income green.
- **Tagline (optional):** "Family money, added up."
- **Not chosen** on the design canvas: B "Kin plus" (a plus sign with four coloured family dots) and C "Home monogram" (a K under a roof line).

### Visual design system

The look comes from the UI UX Pro Max skill's recommendations for a personal finance tracker: a clean, minimal "Swiss" style built for dashboards, in dark and light themes.

| Token | Dark | Light | Used for |
| --- | --- | --- | --- |
| Background | #0F172A | #F1F5F9 | Page (never pure white) |
| Surface | #192134 | #FFFFFF | Cards, panels |
| Primary | #1E40AF | #1E40AF | Buttons, active nav, selected states |
| Link / accent | #60A5FA | #1E40AF | Links, projected balance line |
| Income | #34D399 | #047857 | Income amounts, positive changes |
| Over / warning | #F87171 | #B91C1C | Over budget, increases worth noticing |
| Muted text | #94A3B8 | #475569 | Labels, secondary text |

- **Fonts:** IBM Plex Sans for text; IBM Plex Mono with aligned (tabular) digits for amounts.
- **Category colours:** each category has a hue for its icon tile and bars (housing violet, travel blue, food amber, transport slate, shopping pink).
- **Rules from the skill's checklist:** text contrast at least 4.5:1, visible keyboard focus, line icons (never emoji), hover transitions of about 200 ms, and no animation when the computer's reduced-motion setting is on.
- **Colour never works alone:** amounts always carry + or − and an "Over" label, so the app still reads without colour.

## Security and privacy

The app handles your most sensitive data, so privacy is a design rule, not an add-on.

- **Encrypt at rest** — SQLCipher (encrypted SQLite) or OS-level disk encryption; app lock with a passcode.
- **Store only what's needed** — mask account numbers to the last 4 digits; delete uploaded statement files after import (optional keep, encrypted).
- **AI is opt-in** — limited to two uses with strict redaction; full rules in the AI usage policy below.
- **No bank credentials** — v1 uses uploads only, so no passwords are ever stored.
- **Later, if hosted (Option B)** — HTTPS, separate logins for each adult member with 2FA, row-level security so only your household can read its data, encrypted backups.
- **Backups** — one-click encrypted export so you never lose history.

**Statements folder:** the bank files in it are not encrypted by the app, so keep the folder inside your own Windows user folder (never inside the code repo) and turn on BitLocker device encryption. The app only reads the folder and keeps its own encrypted copies.

### AI usage policy

AI is allowed for exactly three jobs (the third, Ask Kinsum, arrives in Phase 5), and account numbers and account holder names never leave the app under any circumstance.

| Job | When it runs | What is sent | Never sent |
| --- | --- | --- | --- |
| Categorize | Only for a merchant no rule, memory or keyword has matched before | Cleaned description, amount, date, your category names | Account number, holder name, address, balances, account name or nickname, institution name, owner |
| Learn a PDF layout | Only the first time a statement layout is seen | Redacted text of a few sample transaction lines and column headers | Statement header and footer, account number, holder name, address, balances |
| Ask Kinsum (turn a question into a query) | Only when you ask a question that is not a saved report | Your question with family names replaced by placeholders, table and column names, category names. Optional summaries (off by default): totals only | Transactions, amounts, balances, account numbers, nicknames, holder names, member names |

**How redaction is enforced (in code, before every AI call)**

1. **Allow-list, not block-list** — the AI request is built only from approved fields; nothing else can be attached.
2. **Crop the PDF** — only the transaction table region is extracted; the header and footer (where name, address and account number live) are discarded locally.
3. **Scrub** — replace any run of 4+ digits that is not an amount or date, card-number patterns, and the names of all household users with `[REDACTED]`.
4. **Block on doubt** — if a known account number or user name is still detected after scrubbing, the call is cancelled and the item goes to the Review inbox for you instead.
5. **Learn once** — results are saved (merchant memory, layout template) so AI is not needed again for that merchant or layout.
6. **Audit log** — every AI request is logged with exactly what was sent, viewable in Settings.

## Phased roadmap

Build in four phases so you can start using the app after Phase 1 and refine it with real data, then add Ask Kinsum as Phase 5.

| Phase | Builds | Outcome |
| --- | --- | --- |
| **1 · Foundation** | Repo and Windows launcher; encrypted database and app lock; household members and passcodes; accounts and owners; categories with icons; CSV and PDF import; duplicate and transfer detection | One private ledger |
| **2 · Organize** | Rules; merchant memory; AI for new merchants; tags and bulk edit; "spent by"; review inbox; statements folder, import activity log and undo import | Mostly sorted for you |
| **3 · Understand** | Dashboard; month to month; merchant analysis; "why it is different"; unusual charge alerts; monthly family review; calendar; balance sheet; look back by date | Where money goes |
| **4 · Plan ahead** | Recurring detection; upcoming items and safe to spend; budgets and alerts; savings goals; subscription audit; fees and interest watch; merchant limits; month-end review; splits; backup and installers | Budget and plan |
| **5 · Ask Kinsum** | Questions and reports in plain English; saved reports; optional written summaries | Answers on demand |

Each phase ends with a check-in: your family tries it on your own statements, and we adjust the next phase before building it.

- **Phase 1 is the biggest** — PDF import has to work from day one because some of your banks only offer PDF. If it feels too large, split it: CSV import first, then PDF.
- **Encryption and the app lock come first** because real bank data goes in from the first import.
- **Recurring detection sits with budgets in Phase 4** because budget suggestions and fixed bills depend on it, and it works best on fully categorized history.
- **Merchant analysis waits for Phase 3** because it needs the merchant grouping built in Phase 2.

**Phase 5 · Ask Kinsum** — questions and reports in plain English, saved reports, optional written summaries. It comes last because it needs the finished data model and the Phase 3 reports to check its answers against.

## Decisions

Your answers settle the build; no open questions remain, so Phase 1 can start once you approve this plan.

| Question | Decision | What it changes |
| --- | --- | --- |
| Where it runs | Option A — local app on a Windows laptop for now (Mac later); hosting later | No hosting cost; data stays on your computer. Built so it can move to hosted later without a rewrite |
| Statement formats | CSV and PDF, varying by institution | Per-institution profiles for both; PDF moves into Phase 1 |
| AI use | Three uses only: categorize transactions not recognized before, learn new PDF layouts, and (Phase 5) turn Ask Kinsum questions into read-only queries | Account numbers and holder names never sent; see AI usage policy |
| Currency | USD only | No currency conversion needed |
| Users | Any number of family members | One app on the laptop with a passcode for each adult; members can be added any time; each account belongs to one member or is shared by several; reports filter by any member or group |
| History at start | Six months | Enough for budget suggestions and recurring detection on day one |
| Budget style | Fixed monthly amounts per category | No zero-based mode in v1 |
| Investment valuation | Statement value only | No live price feed |
| App name | Kinsum | Repo kinsum, data folder Kinsum, logo concept A (see Name and logo) |

**Code:** kept in your own private GitHub repository; real statements and the database never go into it (see GitHub repository under Tech stack).

Any change you make to these decisions later goes here first, then into the affected sections.

## Related

- `claude/development-prerequisites.md` — checklist before development starts
- `claude/install-and-move-guide.md` — running, installing, the statements folder, and moving the app and data
- Wireframes and logo: "Kinsum Wireframes" design canvas

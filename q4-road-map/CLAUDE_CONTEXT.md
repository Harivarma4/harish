# CLAUDE CONTEXT — Q4 Road Map

> **Read this first in every new session.** It links the original claude.ai conversation
> ("Director questions and quarterly retrospective") to future Claude sessions.
> **Separate from Project Atlas AI** (the rest of this repo). Don't mix context.
>
> **Labels:** **CONFIRMED** = said or decided by Harish · **IMPLEMENTED** = built and verified
> (POC, deck, doc, ticket pack) · **ASSUMED** = inferred, not confirmed · **OPEN** = not decided ·
> **REJECTED** = considered and turned down.
>
> **Source:** claude.ai export (2026-10-04), conversation `3fdf88c0-54e6-477c-b937-b9483f53e61f`,
> 169 messages, 2026-09-24 → 2026-10-04. Share link: https://claude.ai/share/83f394f3-957d-4900-bb6c-757c13785c9e.
> claude.ai project "Q4 Road Map" (`01a105b8-f59f-71b6-8943-3ec22878fb50`) was created 2026-10-04 07:02 UTC
> and is empty (no docs, no instructions).
> Raw export lives in `q4-road-map/export/` (git-ignored; holds full account history).
>
> Last updated: 2026-10-04 (recovery session; PII guide finished).

---

## 1. Project Objective
**CONFIRMED.** Harish, Data Engineering Manager at **VOZIQ AI**, is preparing a **Director-level Q4 2026
(Oct–Dec) Data Platform Roadmap** with a Q3 retrospective ("What Q3 taught us"). The work moves the team
from project-based data engineering (per-client scripts) to a standardized, governed, secure platform.
Each initiative has an architecture, a **working POC**, GitLab tickets, a capacity plan and a deck.

## 2. Original Requirements (24 Sep, msg #2)
**CONFIRMED.** A long prompt asked Claude to act as "Senior Data Strategy Analyst / Enterprise Data
Architect / Engineering Leadership Advisor", to **challenge and not simply agree**, and to produce:
retrospective (deliveries, wins, challenges, root causes, lessons) · evaluation of 7 proposed initiatives
(PII governance, ingestion platform, client modules Git + AI docs, least privilege, access-request UI,
DW standards) · missing initiatives · 5–7-initiative roadmap with Month 1/2/3 · prioritization · KPIs ·
Director Q&A · 90-second opening · 5-minute narrative.
Required arc: **Standardize → Govern → Secure → Automate → Scale → Enable Self-Service**.

## 3. Current Requirements (latest state)
**CONFIRMED.**
- **One quarter only** (Q4 2026), not four quarters (28 Sep).
- **Team of 4** owns everything: Harish (lead), Suma (Data Engineer), Vatsal (Jr Data Engineer),
  Bhargavi (Jr Data Engineer). Don't write "manager" or "key resource" in the deck (3 Oct, 29 Sep).
- **80/20 split:** 80% roadmap, 20% support for 6 clients (28 Sep).
- **All 6 clients in production by quarter end:** Brinks, GA, Alert360, Frontpoint, Crashplan, Fairway (28 Sep).
- **4 initiatives:**
  1. **Ingestion Platform** ("Sluice", dlt-based)
  2. **PII Governance**
  3. **Least Privilege & Access** (least privilege + service accounts + access requests merged, 29 Sep)
  4. **AI Documentation**
- **GitLab is the ticket tool** (29 Sep, ADR-07 Accepted 30 Sep).
- Deck style: cream background `#F4F1EA`, teal accent `#0E7466`, IBM Plex fonts, speaker notes on every slide.
- Working style: Harish dictates by voice (run-on, self-correcting). **Restate your understanding first**
  ("let me know what you understood"), **debate and challenge**, prefer **comparison tables**, add slides
  rather than replace without asking, be a **partner/mentor**, not only an assistant (4 Oct).

## 4. Requirement Changes (chronological)
| Date | Change | Status |
|---|---|---|
| 24 Sep | 8 engineers assumed → **only 4 engineers incl. Harish**; 6 live clients + WW and Cove trials | CONFIRMED |
| 24 Sep | Ingestion = Harish's existing dlt project (own Claude project), not a generic framework | CONFIRMED |
| 28 Sep | **WW & Cove pilots deprecated**; deliverable = onboarding existing clients onto the platform | CONFIRMED |
| 28 Sep | **1 quarter, not 4** (deck rebuilt from "Q4 2026 → Q3 2027" to Q4 only) | CONFIRMED |
| 28 Sep | Lessons-learned slide placed first (slide 2) | IMPLEMENTED |
| 28 Sep | Owners = the 4 engineers; 80/20 split; all 6 clients live by 31 Dec | CONFIRMED |
| 29 Sep | Least Privilege + Service Accounts + Access Requests → **one initiative (E3)** | IMPLEMENTED |
| 29 Sep | GitLab = ticket and access-request tool (ADR-07 Accepted) | CONFIRMED |
| 29 Sep | Waves: W1 Fairway+Alert360, W2 Brinks+GA, W3 Frontpoint+Crashplan; W2 configured by **Vatsal**, W3 by **Bhargavi** | CONFIRMED |
| 1 Oct | Least privilege covers 4 data users (sandbox app, Jenkins, Jupyter, Superset BI); roles bound to **AD groups** | CONFIRMED |
| 2 Oct | Roles **per data source**; **Jenkins = one service account per client**, the only writer; analysts read prod, create views only in `sandbox`; prod view changes only via **Git → MR → client's Jenkins job** | CONFIRMED |
| 2 Oct | **No emergency side door**: even urgent fixes go through Git + Jenkins; nightly drift job dropped | CONFIRMED |
| 2 Oct | PII: masking at the **data level** (mask at write, "Option A"); only a per-client **CDS** account sees clear **address** data, read through PostgreSQL, audited | CONFIRMED |
| 3 Oct | Ingestion credentials = existing per-client service accounts as **environment variables**, managed by the **Systems team** (no new secrets store or tenant layer) | CONFIRMED |
| 3 Oct | **Encryption moved after Q4** | CONFIRMED |
| 3 Oct | Masking happens **inside the ingestion platform** on every source→destination load | CONFIRMED |
| 3 Oct | "Security team" → "Systems / System Architecture team" throughout | IMPLEMENTED |
| 3 Oct | Q3 lessons rewritten (4 rows; "One SQL Server carries everything" removed) | IMPLEMENTED |
| 3 Oct | Harish's PowerPoint edits merged back into the live deck (v33) | IMPLEMENTED |
| 3 Oct | **Auto-detect PII with Microsoft Presidio**; unknown columns are **masked provisionally** instead of holding the file | IMPLEMENTED |
| 3 Oct | **Every PII value becomes the literal text "PII MASKED"**; no keyed hash, no last-4, no year-only, **no hidden join keys** for email/phone in Q4; derived values (age band) only on request | CONFIRMED + IMPLEMENTED |

## 5. Architecture
**CONFIRMED / IMPLEMENTED in POCs.**

### 5.1 Data flow (per client)
```
Client files / client DB pulls
   → landing/ (Azure Blob | S3 | MinIO | SFTP)     ← raw; only the client's Jenkins account; deleted after verified load
   → Ingestion platform (dlt engine, worker)       ← PII register applied on EVERY load ("mask at write")
        ├─ curated Parquet  client_x/source_NN/*.parquet   (masked; PII shows "PII MASKED")
        │      read by PostgreSQL views via pg_duckdb read_parquet(), SQL Server, Superset, sandbox
        └─ PostgreSQL pii_address.customer_address  (address + customer key, clear)
               SELECT only for svc_cds_<client>; every read audited by pgaudit (pii_auditor role)
   CDS writes enrichment results to one table (e.g. enrichment.neighbourhood); the external API is out of scope
```
- Views keep reading `*.parquet` in the same folders; only the contents change (masked). One-time
  **backfill** per client: mask history to a temp folder → verify row counts + leak scan → swap in place →
  delete clear originals → restart deltas. Steady state: **0 long-term raw copies** (optional raw `archive/`,
  Jenkins-only, client-key encrypted, fixed retention, is **OPEN**: depends on client contracts).
- Unknown column in a delta → Presidio detects it → **masked provisionally**, file still loads, a GitLab issue
  goes to the steward → the steward confirms via MR to the register. Strict mode `unknown_columns: hold` brings back holding the file.

### 5.2 PII register (Git YAML, changed only via MR, steward approves)
- Rules (after 3 Oct): **`keep` | `mask` | `address`**. `mask` → the literal text "PII MASKED"; `address` →
  "PII MASKED" in curated output plus the clear value in the CDS-only table. Empty stays empty. Legacy rule
  names (hash, last4, year_only, blank) are read as `mask`.
- Tiers (still a **draft**, OPEN): Restricted, Confidential, **Address** (fixed decision), Internal/Public.
- Presidio Analyzer only (spaCy `en_core_web_lg`, pattern/checksum recognizers, custom UK postcode /
  phone / account-ID recognizers, context enhancer), run on ~200 sampled values per new column;
  ≥80% of values matching = "sure". **The Anonymizer is not used** (it works on text spans, salts randomly, and is too slow per row).
  Regex fallback when Presidio isn't installed. Indian formats (Aadhaar, PAN, local phones) need recognizers
  before go-live (part of PII-03).

### 5.3 Least privilege & access
- **People:** GitLab request → Systems team adds them to an **AD group** → the group is bound once to a role per data source.
  Groups named `DP-<CLIENT>-<PERSONA>`; Superset viewer/editor (`DP-<CLIENT>-BI-VIEWER`, `-BI-EDITOR`);
  `DP-SUPERSET-ADMIN` (1–2 people). Earlier design: 5 groups per client, 30 total.
- **PostgreSQL** can't read AD → a **sync job** (every 15 min) maps AD groups to roles (Vatsal builds it).
- **Roles per client DB:** `<db>__prod_owner` (NOLOGIN, owns curated/reporting) · `<db>__deployer`
  (Jenkins only, becomes prod_owner) · `<db>__ingest_writer` · `<db>__reader` · `superset_<client>_reader`
  (hidden from SQL Lab) · `app_reader` · `<db>__sandbox_rw` · `superset_<client>_sandbox`
  (`statement_timeout='5min'`) · `svc_cds_<client>`. In the POC, Jenkins can write the address table but
  **can't read it back** (owner role with no members).
- **Jenkins:** one service account per client; the only writer (loads + deploys view scripts). Rule: "only
  Jenkins changes structure; CDS writes data to one table".
- **Prod view change path:** build in sandbox → MR in the client repo (`reporting/<view>.sql`) → CI (no sandbox
  references, test-run in a rolled-back transaction, warn on dropped/renamed columns) → review → client's Jenkins
  deploy job (main branch only). "Urgent fix" label = 1 approver.
- **Superset:** SQL Lab only on the sandbox connection; the `SQL_QUERY_MUTATOR` adds `/* superset_user=… */`;
  analysts reusable logic → virtual datasets.
- **Built-in superusers** (`postgres`, `sa`, Superset `admin`) locked; passwords in the vault; DR only.
  `postgres` restricted to the local socket in `pg_hba.conf`. The DB admin group stays empty except for planned platform work.
- **Records:** GitLab requests, Jenkins logs, Superset query history, pgaudit (LP-04 cleanup needs 30 days of audit logs).
- People never read Parquet directly; only service identities touch storage.

### 5.4 Ingestion platform ("Sluice")
- Harish's existing code at **`D:\ingestion-platform`** (Windows PC; earlier path `D:\Harish\Ingestion-Platform`):
  dlt (pyarrow backend; connectorx rejected because it silently corrupts decimals and timestamps), FastAPI API,
  PostgreSQL job store, Celery workers on Redis, a React UI that **already calls the real API** (CONFIRMED 30 Sep).
- POC additions (30 Sep, `q4-poc` branch as a patch in `q4-poc.zip` + `APPLY.md`, **not yet applied**,
  because the PC disconnected): a scheduler (croniter, per-pipeline time zone, PostgreSQL advisory lock), automatic
  retries (`retry_at`), recovery of tasks whose worker died, Teams/Slack alerts, reconciliation against legacy
  CSV/Parquet in DuckDB, a 14-day cut-over readiness check, configs in Git (`plan` on MR, `apply` on main), and 4 UI
  "Operations" pages. 224 unit tests pass; a 71 s full-stack demo with 5 scenarios passes. It also fixed a bug in the
  existing code (a local/SFTP target whose folder already existed failed on first load).
- Deck slides 10a (architecture) and 10b (3 UI screenshots from the demo build, "Northwind Data" sample data).

### 5.5 AI documentation
- Every night, read each client DB's **structure** (never data) into Git → on MR, draft docs and a change note for the
  changed objects only → merge = approved → publish to Notion (one page per object); a reviewer's text is never
  overwritten; a PII guard masks emails/phones/cards before the AI sees anything. `DOCGEN_DRAFTER=claude` +
  `ANTHROPIC_API_KEY` for live runs (the POC used a rule-based stand-in). ADR-08 covers the AI tool and data policy (Systems/Security sign-off).

## 6. Technology Stack
PostgreSQL 16 (+ pgaudit, pg_duckdb), DuckDB, SQL Server, Parquet, Azure Blob / S3 / MinIO / SFTP, dlt +
pyarrow, FastAPI, Celery + Redis, React (Sluice UI), Superset, JupyterHub/Jupyter Lab, Jenkins, GitLab
(tickets, MRs, CI), Active Directory (Entra ID sync **OPEN**), Microsoft Presidio (spaCy), Notion, Teams/Slack.
Legacy or adjacent: Pentaho, BCP, Snowflake, OneUptime/OpenTelemetry.

## 7. Repository / Project Structure
- This folder: `q4-road-map/` in `Harivarma4/harish` (branch `claude/upbeat-wozniak-reh99v`).
  `CLAUDE_CONTEXT.md` (this file), `README.md`, `export/` (git-ignored raw export + extracted text:
  `dialogue.txt`, `human_only.txt`, `assistant_text.txt`, `msg166_tools.txt`).
- **The POC code is NOT in this repo.** It was built in the old claude.ai sandbox and delivered to Harish as zips
  (see §21). The ingestion code lives on Harish's PC at `D:\ingestion-platform`.

## 8. Database / Data Model (key objects)
- `pii_address.customer_address` (source, customer_id, address_line1, city, postcode…); CDS-only, audited.
- `enrichment.neighbourhood` (CDS results; not PII).
- `audit.ddl_log` + an event trigger were proposed, then **REJECTED** as unnecessary (GitLab + Jenkins + pgaudit cover auditing).
- pgaudit: `pgaudit.role = 'pii_auditor'` with SELECT on PII tables (object audit).
- Legacy SQL Server framework design (Q3): `ctrl.PIIColumnRegistry`, `ctrl.usp_GeneratePIIControls`.
- Example one-time role script (Brinks), 2 Oct:
```sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA reporting OWNER TO brinks__prod_owner;
GRANT USAGE ON SCHEMA reporting TO brinks__reader, brinks__sandbox_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE brinks__prod_owner IN SCHEMA reporting
  GRANT SELECT ON TABLES TO brinks__reader, brinks__sandbox_rw;
GRANT USAGE, CREATE ON SCHEMA sandbox TO brinks__sandbox_rw;
GRANT brinks__prod_owner TO brinks__deployer;       -- the only way to change production
GRANT brinks__reader TO superset_brinks_reader;
GRANT brinks__sandbox_rw TO superset_brinks_sandbox;
ALTER ROLE superset_brinks_sandbox SET statement_timeout = '5min';
```

## 9. APIs / Integrations
GitLab API (bootstrap script; tested only against a mock GitLab and a local stand-in), Notion (dry runs),
Teams/Slack webhooks (SSRF-guarded), AD/LDAP (simulated with a YAML file in the POC), Anthropic API (AI docs,
not run live), and Superset `SQL_QUERY_MUTATOR`:
```python
from superset.utils.core import get_username
def SQL_QUERY_MUTATOR(sql, **kwargs):
    return f"/* superset_user={get_username()} */\n{sql}"
```

## 10. Infrastructure / Deployment
Ingestion needs 5 containers (API, UI, worker, scheduler, Redis) plus PostgreSQL; hosting is ADR-10, owned by Infra, **OPEN**.
Credentials come from the Systems team as environment variables. Deploys go only through Jenkins from main.

## 11. Implementation Completed (all **IMPLEMENTED** in the old session)
| Deliverable | Where | State |
|---|---|---|
| **Data Platform Roadmap — Q4 2026** (main Director deck, ~45 slides incl. 06a/10a/10b/17a/17b/20a/20b/20c) | https://claude.ai/artifact/HrmGmB3wfj9BjsTcbFRomE (title on creation "…Q4 2026 to Q3 2027") | **v35** (3 Oct) |
| GitLab Delivery Plan doc ("Q4 2026 Data Platform Roadmap – GitLab Delivery Plan"; Main, Backlog, Traceability tabs) | https://claude.ai/code/artifact/099e8497-47e1-439a-a7f3-3b7972e01dec | current to 3 Oct |
| GitLab import pack `q4-2026-gitlab-import-pack.zip` (bootstrap script, CSV, labels, milestones, templates, `owners.json`) | delivered to Harish | **116 issues**, ~117 links, 5 epics, 59 labels |
| AI Documentation – Architecture and POC (doc) + `ai-docs-poc.zip` (35 tests) | https://claude.ai/artifact/GsUUqvCT7RDXWkmTNmDJTZ | done 29 Sep |
| Least Privilege & Access – Architecture and POC (doc) + `accessctl-poc.zip` (28 tests, PG16 + pgaudit) | https://claude.ai/artifact/9icqtG68X4PFfri4GtyXwK | done 29 Sep; **updated 4 Oct** (new "Agreed design (2 October)" section + diagram; persona/binding tables, rollout LP-14..17, env-var credentials, waves named) |
| PII Governance – Architecture and POC (doc) + `piictl-poc.zip` (22 tests; 10 review findings fixed) | https://claude.ai/code/artifact/56dbe4fb-a140-416e-9f26-32349b589d4c | done 30 Sep; **updated 4 Oct** ("What changed on 2–3 October" table; architecture diagram redrawn; classification = Presidio + provisional; protection = "PII MASKED" + CDS table; decisions, rollout incl. PII-17/18, PII-16 after Q4) |
| Ingestion Platform – Architecture and POC (doc) + `q4-poc.zip` (224 tests) | https://claude.ai/code/artifact/592877c3-9309-4ebc-b8af-0daf544ab610 | done 30 Sep |
| `platform-poc.zip` (`platctl`: role scripts, mask-at-write, AD sync, Git-only deploys, Presidio `detect.py`) | delivered | **64 demo checks, 30 tests pass** (3 Oct, "PII MASKED" version) |
| Teams message to the Director (2 versions) | chat widget | 3 Oct; the line asking the Director to name a data owner per client should become the Systems team availability ask |
| Earlier decks (superseded) | Q3 Retro & Q4 (CkV6qDZMJVeti7m7CYTHVb), From Projects to Platform (EhW2t35KbSSeC5rkz1C7SW), Q4 Initiatives 4-person (647HyrkTcGymrwepwAT8GH), Lessons Learnt and Roadmap (CHSq2VrDScqzFZuJciCFLm) | still mention WW/Cove |
| **PII protection guide** (education doc) | https://claude.ai/code/artifact/b27c187c-0f2c-4f29-be0e-2f5beb92f3a0 | **complete** (rev 9, 4 Oct, recovery session): 7 sections |

## 12. Important Technical Decisions
- **ADRs:** ADR-01 Ingestion service architecture (keep FastAPI + PG job store + Celery/Redis, add a scheduler; Proposed, due 16 Oct) ·
  ADR-02 dlt + pyarrow (Accepted, recorded retroactively) · ADR-03 role model · ADR-04 secrets store (Proposed/Infra;
  **largely superseded** by environment variables) · ADR-05 where the PII registry lives (Proposed) · **ADR-06 PII protection pattern =
  mask at write, "PII MASKED"** (Proposed by Harish 3 Oct) · **ADR-07 GitLab for access requests (Accepted 30 Sep)** ·
  ADR-08 AI docs architecture & data policy · ADR-09 identity source (AD/Entra/SSO; Proposed) · ADR-10 container hosting
  (Infra) · ADR-11 schedules in the platform (croniter + advisory lock) · ADR-12 parallel runs proven by reconciliation +
  14-day readiness · ADR-13 configs in Git.
- Approach **A (mask at write) chosen over C (Parquet column encryption)**: SQL Server and DuckDB can't read
  column-encrypted Parquet, and readers without the key get errors instead of masked values. C stays a future option if engines change.
- Address tier = a **real table**, not a pg_duckdb view over raw (a view over `read_parquet()` would let the reader read any file).
- Capacity basis: 10 working weeks (Dussehra, Diwali, Christmas, leave removed); engineers 32 h/week on the roadmap;
  Harish 20 h/week (ASSUMED 50%, never corrected by Harish).

## 13. Rejected Approaches (**REJECTED**)
- Access-request **custom UI** in Q4 (a GitLab workflow instead) · a new secrets store / tenant layer for ingestion ·
  Airbyte (its metadata columns break clean Parquet) · connectorx · **Approach C** column encryption ·
  masking only inside each engine (B), as a primary control · keyed HMAC hash / last-4 / year-only / blank rules ·
  Presidio Anonymizer for masking · hidden join keys for email/phone in Q4 (deferred) · nightly drift comparison job ·
  DDL event-trigger audit log · emergency admin side door · WW & Cove pilots · a 4-quarter roadmap ·
  CDS tokens (dropped for now; revisit if CDS ever gets access to names).

## 14. Problems Encountered
- Capacity: per-person load swung from 132% (equal split) to 54–64% (80/20) to 87–95% in a realistic hours view.
- Vatsal is the single point of failure on ingestion (risk **R19**); Bhargavi pairs with him as cover.
- Remote link to Harish's PC (remote-devices tools) disconnected before the `q4-poc` branch could be written.
- pg_duckdb not installable in the sandbox; SQL Server, live GitLab, Notion and AD were never tested live.

## 15. Errors and Solutions
- Ingestion review found 8 bugs (duplicate task execution, scheduler self-lockout, SSRF in webhooks, cross-tenant
  reconciliation path, customer values in alert text); all fixed with tests.
- PII review found 10 bypasses (worst: lowering a tier without owner approval by editing discovery output); all fixed.
- Least privilege review: a request could be edited after its checks to grant 10-year prod write; fixed (the grant job uses only the recorded checks).
- AI docs review: a re-draft could overwrite reviewer edits; an AI outage failed the whole step; GitLab CI errors. All fixed.
- Existing Sluice bug: a local/SFTP target whose folder already existed failed on first load. Fixed in the patch.
- This session: claude.ai share and export download links return **Cloudflare 403** from the cloud sandbox; the user downloaded the zips manually.

## 16. Current Implementation
See §11. Latest artifact versions: **deck v35**, **ticket pack 116 issues**, **platform-poc 64 checks / 30 tests**.

## 17. Current Open Issues (**OPEN**)
- Secrets store still appears in LP slides (20c, 21, 22), Oct/Nov/dashboard slides, dependencies, ownership, current state, one-pager, summary,
  and in tickets **EXT-01, LP-07**. PII-16 (encryption, 32 h of Suma's work) is still a Q4 "Could"; it should move after Q4.
- ING-02 ("replace the mock API") is still open in the plan and deck, but it's already done in the code.
- `q4-poc` patch not applied to `D:\ingestion-platform`.
- The "E3 Access Initiative Status" page still says ACC-05 is waiting on build-or-buy.
- Check with analysts: no report or model may join or count customers by email/phone in Q4 (decision 06 on the asks slide).
- ADR-09 / Entra ID sync for Azure Blob group access (question for the Systems team).
- Client contracts: raw retention and permission to send addresses to the enrichment API.
- GitLab tier (Premium/Ultimate?) decides nested epics and enforced MR approvals.
- Q3 evidence on the lessons slide and the baselines/KPI brackets still need Harish's real numbers.
- Old decks still mention WW/Cove.

## 18. Pending Tasks
- [x] Finish the PII protection guide (done 4 Oct, recovery session).
- [x] Update the PII Governance and Least Privilege docs with the 2–3 Oct architecture (done 4 Oct).
- [x] Deck (v37, 4 Oct): secrets store removed from 16 slides (current, dashboard, dependencies, evolution, ing-architecture,
      ing-phases, ing-reuse, ing-ui, lp-kpis, lp-phases, lp-split, nov, oct, onepager, ownership, summary); mock-API text
      replaced (UI already calls the real API); ing-architecture "new column: held" → "masked". Deck already had PII-16/encryption after Q4.
- [x] Delivery Plan doc (main + Backlog tabs, 4 Oct): EXT-01 → "Service-account credentials as environment variables (Systems team)",
      ING-09 / LP-07 reworded, ADR-04 → Superseded (3 Oct), ING-02 → Done, PII-16 → After Q4 (FX.2), PII-16 removed from week tables.
- [x] GitLab import pack rebuilt (4 Oct; copy in `q4-road-map/export/`, git-ignored): plan.json edited, issues_import.csv and backlog_full.md
      regenerated from it (verified byte-identical regeneration first). EXT-01/ING-09/LP-07/F3.2 reworded; EXT-01 team::infra → team::leadership;
      ING-02 status::done, estimate removed, all boxes ticked; bootstrap_gitlab.py now closes status::done issues on create;
      PII-16 → FX.2, moscow::wont-q4, After-Q4 milestone, no due/estimate. Q4 issues 96 → 95; Suma 19 → 18.
      Checks: `--offline` (58 labels, 4 milestones, 5 epics, 116 issues, 117 links) and a mocked `--apply` (116 created, only ING-02 closed).
      The pack has no generator script (plan_data.py stayed in the old sandbox): edit plan.json, then re-render CSV/backlog (packlib logic).
- [x] Capacity updated (4 Oct, deck v38 + delivery plan): Suma 264/320 (83%, 26 of 32 h/wk), team 1,009/1,160 (87%), range 83–91%; plan ticket hours 1,140 → 1,108.
- [x] **Team name decided 4 Oct: "Systems Architecture team"** (Harish). Deck v38: every "Systems team" / "System Architecture Team" / "System’s team"
      and the team-sense "Security" renamed (acc-kpis, acc-workflow, current, ing-*, lp-*, nov, oct, ownership, pii-framework). Left as is on purpose:
      risks slide "Type: Security" (a category), "Security questionnaires", "Security classification", "Security work starts".
      NOT yet renamed: PII/LP/AI-docs/delivery-plan docs and the ticket pack still say "Systems team" / "Security" — offer.
- [ ] OPEN (4 Oct): Harish thinks the ingestion **job store is Q4 work, not built**, and said "if it is built, I want that architecture".
      The 30 Sep read of D:\ingestion-platform found it BUILT: PostgreSQL via SQLAlchemy + Alembic (4 migrations: jobs, tasks per object,
      events per phase, watermarks, validation results, metrics; app/models/entities.py), Celery on Redis workers, FastAPI API, 210 tests.
      Gaps were operational (scheduling, retries, stuck-task recovery, alerts, configs in Git, reconciliation). Deck slide 10a still says
      "Job store · Q4 build" and current/ing-reuse say "No durable job state". DECIDED 4 Oct: "built matches your code" → mark the job store as built.
      Drafted (NOT yet published, awaiting Harish's OK): slide 10c `ing-jobstore` (task states PENDING→RUNNING→SUCCESS/FAILED, RETRY_WAIT,
      reaper, atomic claim, fencing; green = in code, orange = Q4 POC) and slide 10d `ing-tables` (real tables from app/models/entities.py:
      connections, targets, pipelines, pipeline_objects | jobs, job_tasks, job_events, validation_results, watermarks, job_metrics |
      Q4 migration 0005_q4_operations: schedules, alert_channels, alert_deliveries, reconciliation_specs, reconciliation_runs + job_tasks.heartbeat_at/retry_at;
      also tenants, users, secrets, audit_events, templates, uploads). Copies + PNG previews in `q4-road-map/drafts/`.
      Also prepared locally (unpublished): "built" wording on ing-architecture, current, ing-reuse, evolution, ing-phases, nov, onepager.
      On publish: re-read project/deck.json, insert ing-jobstore + ing-tables after ing-ui.
      Noted, not changed: ing-reuse says "no server-side auth" but code has JWT + five RBAC roles.

- [ ] Apply `q4-poc` when the PC is linked (or Harish follows `APPLY.md`).
- [ ] Fix the Teams message (Systems team ask instead of data owner).
- [ ] Week-1 tasks from the plan: GitLab governance project, name stewards and approvers, **audit logging on by 12 Oct**,
      inventory on Fairway + Alert360 in the week of 26 Oct, wave 1 parallel run by **16 Nov**.

## 19. Important Constraints
- 4 people, 1 quarter, 6 clients live by 31 Dec; cut-overs 30 Nov – 18 Dec; nothing new after 20 Dec.
- Waves: W1 Fairway+Alert360 (config Suma; parallel run 16–27 Nov; cut-over 30 Nov–4 Dec; runs by Vatsal) ·
  W2 Brinks+GA (config **Vatsal**; parallel 23 Nov–4 Dec; cut-over 7–11 Dec; runs by Bhargavi) ·
  W3 Frontpoint+Crashplan (config **Bhargavi**; parallel 30 Nov–11 Dec; cut-over 14–18 Dec; runs by Vatsal).
- 14 clean parallel days before each cut-over; 30 days of audit logs before access cleanup.
- **Capacity (latest, 3 Oct): ~1,041 of 1,160 hours (90%)**. Suma 296/320 (93%, tightest because of PII-18);
  earlier 3 Oct figures: Harish 176/200, Vatsal 278/320, Bhargavi 291/320.
- No new spend (open source: dlt, DuckDB, Presidio, GitLab, Jenkins).
- POC sample data is made up; no real client data.

## 20. Important Commands / SQL / Scripts
- Role script (§8), Superset mutator (§9), pgaudit object audit (`pgaudit.role='pii_auditor'`).
- `ALTER LOGIN sa DISABLE` (SQL Server); `pg_hba.conf`: `postgres` local only; CDS and app accounts allowed only from their hosts.
- Ticket keys: ING-01…26, PII-01…18, LP-01…17, ACC-01…13, DOC-01…13, GOV-01…08, EXT-01…05, ADR-01…13.
  Notable: PII-03 Presidio scan · PII-07 masking · PII-09 provisional-rule gate · PII-15 leak scan · PII-16 encryption ·
  PII-17 CDS address table · **PII-18 provisional masking + steward review (M, Suma, weeks 8–9)** · LP-14 role scripts ·
  LP-15 AD binding · LP-16 sandbox split · LP-17 lock built-in admins · ACC-05 GitLab access-request project ·
  ING-12 client assessment · ING-14…25 wave issues · GOV-02 agree the 80/20 split.
- Run the old POCs: `pytest` in each zip; the demo is `demo/run_demo.py` (platform-poc).

## 21. Important Files
- Delivered zips (with Harish, not in the repo): `platform-poc.zip`, `piictl-poc.zip`, `accessctl-poc.zip`,
  `ai-docs-poc.zip`, `q4-poc.zip` (patch + `APPLY.md`), `q4-2026-gitlab-import-pack.zip`.
- Harish's uploads: `Q4 Initiatives — Platform Foundations with a Four-Person Team 1.pptx`, `ROADMAP-DECK.html`,
  `Ingestion-Platform.zip` (UI only, no Python), `Data Platform Roadmap — Q4 2026 4.pptx`.
- POC internals mentioned: `platctl/masking.py`, `platctl/detect.py`, `config/pii_register.yaml`,
  `demo/run_demo.py`, `tests/test_platctl.py`, `pyproject.toml`, `README.md`, a Jenkinsfile.

## 22. Conversation Timeline
- **24 Sep:** retrospective and strategy (7 ideas → 3 programs); decks v1/v2; 4-person Q4 deck; meeting points; ingestion 4-phase slide.
- **28 Sep:** slide 9 rework + templates; Lessons Learnt deck; Data Platform Roadmap deck (39 slides, 5 initiatives); WW/Cove dropped;
  1-quarter rebuild; lessons slide first; GitLab delivery plan + import pack (104 issues); owners; 80/20; 6 clients live.
- **29 Sep:** LP+access merged (E3, 4 initiatives); AI Docs architecture + POC; LP & Access architecture + POC; GitLab as ticket tool;
  waves named; W2→Vatsal, W3→Bhargavi; "key resource" removed.
- **30 Sep:** PII Governance architecture + POC (`piictl`); Ingestion architecture + POC via the linked PC (`q4-poc`).
- **1 Oct:** 4 data users + AD groups design (doc section + slide 20a).
- **2 Oct:** capacity in hours (1,057/1,160); long debate on roles per source, pg_duckdb risk, Superset SQL Lab, Git-only prod;
  final LP understanding (slides 20a/20b); PII: CDS address tier, mask-at-write, A vs C comparison, backfill flow.
- **3 Oct:** no two raw copies; architecture applied to slides (v28) + platform-poc + tickets (114); env-var credentials, encryption
  after Q4, no "manager" (v29); slides 10a/10b; Q3 lessons rewrite; Teams message; PPT edits merged (v33); register example;
  Presidio auto-detect (PII-18, v34, 115 issues); Presidio explained; "PII MASKED" decision (v35, 116 issues).
- **4 Oct 06:06:** asked for an education guide on how companies protect PII and where Presidio is used, with Claude as partner/mentor.
  Claude created the doc and filled 3 of 7 sections; Harish said "Resume" at 06:41 and 06:57, and there was **no reply**.

## 23. LAST KNOWN STATE
- **Last user request:** "Educate me on how companies secure their PII, how Microsoft Presidio is used and which companies use
  it; give me a guide; act as my partner/mentor" (4 Oct 06:06), then "Resume" ×2 (06:41, 06:57).
- **Last Claude action:** created the Claude Docs doc **"PII protection: how companies do it, and where we stand"**
  (https://claude.ai/code/artifact/b27c187c-0f2c-4f29-be0e-2f5beb92f3a0; tab `dccc0703-5359`, body node `376dd59e-85e1`) and filled:
  §1 "How companies protect PII" (six-layer diagram: discover ✓, minimise partly, de-identify ✓, access ✓, encrypt after Q4,
  prove partly; governance around them), §2 "The techniques, side by side" (8-technique table + anonymized vs pseudonymized),
  §3 "What the big platforms build in" (Snowflake, Databricks UC, BigQuery, AWS Macie, Microsoft Purview; why we mask at write).
  It then ran 2 web searches for §4 (LiteLLM guardrails; Presidio on Spark/Databricks/ADF) and stopped.
- **Last implementation:** "PII MASKED" rule across POC, deck v35, ticket pack (116), delivery plan (3 Oct 14:38).
- **Last error:** none in the work; the session simply stopped mid-turn.
- **Last decision:** mask everything as "PII MASKED", no hidden join keys in Q4, derived values only on request (3 Oct).
- **Current state:** doc at rev 4 with pending blocks `mxjja2hcr0m.324` (Presidio & adopters), `.325` (Where we stand),
  `.326` (Partner view), `.327` (Sources). Verified readable from this session (2026-10-04).
- **Remaining work:** the §18 backlog (guide finished in the recovery session).
- **Next action:** see §24.

## 24. IMMEDIATE NEXT ACTION
**Done in the recovery session (4 Oct):** the PII guide's §4–§7 were filled in place (rev 9):
§4 Presidio (modules; **Presidio is moving from Microsoft to the community "Data Privacy Stack" org**,
github.com/data-privacy-stack/presidio, MIT, new images at `ghcr.io/data-privacy-stack/presidio-*`, old MCR images frozen,
PyPI presidio-analyzer 2.2.364; documented uses: LiteLLM/AISIX gateways, Spark/Databricks, Fabric, ADF, Azure AI Language;
no public list of named customers), §5 Where we stand (7-row layer table), §6 Partner view (ask analysts / Legal / Systems team
one question each; prove Presidio on a wave 1 feed and pg_duckdb-in-view (LP-16); learning table; push: encryption no later than Q1),
§7 Sources. The lead line was corrected to say Q4 covers discovery, de-identification and access.
Sources in this sandbox: microsoft.github.io, docs.litellm.ai and the Fabric blog are egress-blocked; GitHub raw and PyPI work.

**Done 4 Oct (later):** PII Governance and Least Privilege docs updated in place (Harish said "Yes" to item 1).
LP doc: `4698b159-b4f7-43a2-b8cf-651f793b3416` (body node `486fad98-87f0`, new widget `9f687729-071c`); PII doc body node
`e14ef60e-6ccc`, widget `cf08efd8-3db0` redrawn. Minor: a few replaced paragraphs lost their bold lead-in words (cosmetic).
The AI Documentation doc is `8085341e-5258-4cda-b6ec-924712df29a8`.

**Next:** Harish's call from §18. Recommended order: (2) remove the secrets store from slides and tickets (EXT-01, LP-07), move PII-16 after Q4, mark ING-02 done,
rebuild the pack; (3) consider a Presidio-transition note in ADR/PII-03 (pin version, use ghcr images).

## 25. INFORMATION THAT COULD NOT BE RECOVERED
- The **final contents of the POC code** (the zips were built in the old sandbox; the export holds only tool calls, many edits
  done by inline Python patches). Harish has the zips; ask for them if code work resumes.
- The deck's exact final slide list and HTML (only edits are visible). The deck is reachable at its artifact URL.
- Thinking blocks and full tool outputs beyond what the export stores; the `frames-000.7z` archive (not extracted: no 7z tool).
- The Teams message's final text (widget output not in the export).
- The real Q3 numbers (load-time reduction, incident counts, onboarding days); never provided.
- Whether Harish's 50% roadmap-time assumption is right (never confirmed or corrected).
- The earlier "ingestion platform" Claude project chats (separate project; not in this conversation).

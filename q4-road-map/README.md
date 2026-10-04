# Q4 Road Map

A standalone project, **not related to Project Atlas AI**, which happens to share
this repository. It continues a previous Claude conversation, recovered from a
claude.ai data export.

## Layout

- `CLAUDE_CONTEXT.md` — persistent memory that links Claude sessions (recovered from the export on 2026-10-04). Read it first
  in every new session; update it whenever a requirement, decision,
  implementation or bug changes.
- `export/` — drop the claude.ai export zips here (`conversations-000.zip`,
  `projects-000.zip`, `memories-000.zip`, …). Raw exports are git-ignored
  because they hold your full account history; only the recovered context is
  committed.

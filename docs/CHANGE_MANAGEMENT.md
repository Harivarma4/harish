# Change Management & Release Strategy

A CAB-aligned (Change Advisory Board) process for evolving Project Atlas AI
safely as it scales. It mirrors the platform's own philosophy — controlled
change, evidence, and an auditable trail for every modification.

## Principles

- **Every change is a PR.** No direct pushes to `master`. One enhancement per PR.
- **Small, reversible increments.** Prefer many small PRs over one large one;
  each should be independently revertable.
- **Green before merge.** The automated gate (below) must pass; a red PR is never
  merged — it is fixed first.
- **Conventional Commits** so history, changelogs, and release notes are derivable.
- **Auditability.** The PR (description, review, CI run, merge commit) is the
  permanent record of what changed, why, and who approved it.

## Change classes (CAB)

Borrowed from ITIL, sized to this repo:

| Class | Examples | Approval | Deploy |
|-------|----------|----------|--------|
| **Standard** (pre-approved) | docs, tests, mock-only tweaks, dependency patch bumps behind the gate | Automated gate only | Auto on merge |
| **Normal** (CAB-reviewed) | new adapter/agent, port changes, API schema changes, new dependency | Gate **+ 1 code-owner approval**; risk & rollback stated in PR | Staging → prod |
| **Emergency** | production incident hotfix, security patch | Expedited review (post-hoc CAB note); gate still runs | Immediate, then documented |

The CAB "review" for a solo/small team is the code-owner approval on a Normal
PR; as the team grows it becomes a scheduled review of queued Normal changes.
Classify each PR in its description (the template prompts for it).

## Branching & environments

- **Trunk-based.** `master` is always releasable. Short-lived feature branches
  (`claude/*`, `feat/*`, `fix/*`) → PR → squash/merge → delete.
- **Environments** grow with scale: `dev` (mock adapters, offline) →
  `staging` (real adapters, paper/read-only broker) → `prod` (real adapters,
  explicit user-authorized execution only). Config is 12-factor
  (`ATLAS_*` env vars), never code — the same image ships to every environment.

## Automated quality gate (DevSecOps)

Enforced in CI (`.github/workflows/ci.yml`) on every PR and required to merge:

1. `ruff` (lint) 2. `mypy` (types) 3. `bandit` (security) 4. `pytest` (tests)

Roadmap gates as the codebase grows: coverage threshold, dependency/CVE scan
(`pip-audit`), SonarQube, container image scan, and an import-linter rule that
enforces the hexagonal dependency direction (domain imports nothing outward).

## Review policy

- `.github/CODEOWNERS` routes review; **Normal** and **Emergency** changes need a
  code-owner approval before merge.
- The PR template requires: change class, risk/blast-radius, rollback plan,
  testing evidence, and a checklist (including "research-not-advice disclaimer
  intact" — a domain invariant that must never regress).

## Versioning & releases

- **SemVer** (`MAJOR.MINOR.PATCH`) on `pyproject.toml`.
- **Changelog** in `CHANGELOG.md` (Keep a Changelog format), updated per PR.
- A tagged release (`vX.Y.Z`) cuts release notes from the merged Conventional
  Commits since the last tag.

## Deploying at scale

- **Containerized** (multi-stage, non-root); the same image across environments.
- **Progressive delivery**: blue-green or canary for the API; roll forward on
  health-check + smoke-test pass, roll back automatically on failure.
- **Feature flags** for risky behavior (e.g. enabling a real broker execution
  path) so it can be dark-launched and killed without a redeploy.
- **Stateful concerns** (DB migrations, cache/embedding schema) are forward-only
  and reversible; migrations ship in their own Standard/Normal PR ahead of the
  code that needs them.

## Rollback

Every Normal+ PR states a rollback plan. Default rollback is `git revert` of the
merge commit (re-PR'd) plus redeploy of the previous image tag. Because adapters
sit behind ports and are selected by config, a bad real adapter can also be
disabled instantly by flipping its `ATLAS_*_SOURCE`/`PROVIDER` back to `mock`
without a code change.

## Definition of Done (per PR)

- [ ] Change class stated; risk & rollback documented (Normal+).
- [ ] Full gate green (ruff, mypy, bandit, pytest).
- [ ] Tests cover the change; adapters unit-tested offline via injected fakes.
- [ ] Docs / `.env.example` / `CHANGELOG.md` updated.
- [ ] Research-only guardrails (confidence, evidence, disclaimer) intact.

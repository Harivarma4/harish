# Summary

<!-- What does this PR change, and why? One enhancement per PR. -->

## Change class (CAB)

<!-- Pick one — see docs/CHANGE_MANAGEMENT.md -->

- [ ] **Standard** — docs / tests / mock-only / patch bump (gate-only approval)
- [ ] **Normal** — new adapter/agent, port or API change, new dependency (needs code-owner approval)
- [ ] **Emergency** — production incident / security hotfix

## Risk & blast radius

<!-- What could this affect if it goes wrong? Which ports/agents/env vars? -->

## Rollback plan

<!-- Default: git revert the merge commit + redeploy previous image tag.
     Config rollback: flip the relevant ATLAS_*_SOURCE / _PROVIDER back to `mock`. -->

## Testing

<!-- Commands run and results. Real adapters must be unit-tested offline via injected fakes. -->

- [ ] `ruff check src tests`
- [ ] `mypy`
- [ ] `bandit -q -r src`
- [ ] `pytest`

## Checklist

- [ ] One enhancement, scoped and independently revertable
- [ ] Tests cover the change
- [ ] Docs / `.env.example` / `CHANGELOG.md` updated
- [ ] Research-only guardrails intact (confidence, evidence, **not-investment-advice disclaimer**)
- [ ] No secrets, keys, or credentials in the diff

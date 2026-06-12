---
description: Interview the user (QA Lead + dynamic stack test SME) on test strategy — levels, coverage, tooling, fixtures, CI gating. Produces the optional per-version testing.md that drives testing in planning, execution, and verification.
model: opus
argument-hint: <slug> [--auto]
---

# /pm:test — Test strategy decisions

You are running the `/pm:test` command. The user is deciding the test strategy for this version: what levels of testing exist, what must be covered, what tooling is used, and what gates merges. The output, `testing.md`, is **optional** — when absent the pipeline behaves exactly as before — but **binding when present**: `/pm:plan` shapes acceptance criteria with it, `/pm:execute` writes tests to it, and `/pm:verify` rejects test drift unless the executor documents a justified deviation.

## Inputs
- Slug: `$ARGUMENTS` (use active-project resolution if empty).
- `--auto` (anywhere in `$ARGUMENTS`) — **override mode.** Do not ask the user any questions. At every point where this command would normally interview, confirm, or present an `AskUserQuestion`, instead choose the best option from the PRD / research / architecture / repo signals and your own expertise, state the decision and a one-line rationale inline, and continue. Reserve stopping for hard blockers only (a missing REQUIRED input that cannot be inferred). When a gate would replace an existing artifact, take the **overwrite-with-backup** path automatically (back up / archive first — never lose data). Default (flag absent) = the interactive behavior described below.

## Step 1 — Resolve project and active version

Standard active-project resolution. Read `active_version` from `prd.md` frontmatter.

## Step 2 — Pre-flight checks

- `.pm/<slug>/prd.md` — REQUIRED. If missing, stop and tell the user to run `/pm:prd` first.
- `.pm/<slug>/<active_version>/goals.md` — REQUIRED.
- `.pm/<slug>/<active_version>/architecture.md` — OPTIONAL. If present, its §12 Testing row and stack picks become the defaults for the tooling interview. If missing, note one line ("No architecture.md — tooling recommendations will come from the repo and PRD signals") and continue without asking. Don't gate an optional artifact on another optional artifact.
- `.pm/<slug>/<active_version>/research/test-strategist.md` — if present, this report is the primary seed for your recommendations. Other research files are secondary context.

If `.pm/<slug>/<active_version>/testing.md` already exists, ask via `AskUserQuestion`:
- **Overwrite** — back up the existing file to `testing.md.bak.<timestamp>` and start fresh.
- **Amend** — read the current file and run a focused diff-style interview that only revisits sections the user wants to change. Each change appends to the `## Amendments` section.
- **Cancel** — stop.

Under `--auto`, take **Overwrite** automatically — back up the existing file to `testing.md.bak.<timestamp>` first (overwrite-with-backup), then start fresh.

## Step 3 — Read context

Read fully:
- `.pm/<slug>/prd.md` including Amendments.
- `.pm/<slug>/<active_version>/goals.md`.
- `.pm/<slug>/<active_version>/architecture.md` including Amendments (if present).
- Every file in `.pm/<slug>/<active_version>/research/` (if present) — `test-strategist.md` first.

Detect the repo's existing test setup for brownfield signals:
- Test directories and naming conventions: `src/test/`, `tests/`, `__tests__/`, `spec/`, `*_test.go`, `test_*.py`, `*.spec.ts`, `*.test.tsx`, etc.
- Runner/framework config: `jest.config.*`, `vitest.config.*`, `pytest.ini` / `[tool.pytest]` in `pyproject.toml`, surefire/failsafe + JUnit/Testcontainers deps in `pom.xml`/`build.gradle`, `.rspec`, `playwright.config.*`, `cypress.config.*`, etc.
- Coverage tooling: jacoco, coverage.py / `.coveragerc`, nyc/c8, etc.
- CI: test jobs in `.github/workflows/*.yml` (or other CI config) — what already gates merges.
- Existing fixtures, factories, or `testdata/` directories.

If brownfield, the detected setup is the **default** — recommendations lean toward extending what's already there rather than introducing a parallel harness.

## Step 4 — Adopt the personas

You are simultaneously two interviewers throughout this session. Surface their names so the user knows who is asking what.

**Persona A — QA Lead.** Cross-cutting strategy: test pyramid shape, coverage philosophy, what must and must not be covered, CI gating, flake policy, deliberately out-of-scope testing.

**Persona B — `<Stack> Test SME`.** Pick a stack framing for the SME based on:
1. **Brownfield first:** if the repo has an existing stack, the SME is for that stack (e.g. "Java/Spring Test SME", "TypeScript/Node Test SME", "Python Test SME").
2. **Architecture next:** if `architecture.md` exists, use its language/framework picks.
3. **Greenfield:** propose a framing from PRD signals. State your pick in one sentence at the start and let the user override before continuing. Under `--auto`, state your pick and proceed without waiting for an override.

The SME owns framework/tooling picks, fixture/factory idioms, mocking boundaries, and integration harness choices (e.g. Testcontainers vs in-memory).

Tag every question with `[QA]` or `[SME-<stack>]` so the user knows who's asking.

## Step 5 — Test-strategy interview

Conduct the interview in themed rounds. Each round asks 2–4 questions. Use `AskUserQuestion` for discrete choices; free-form prose for open-ended exploration. **Every multiple-choice question lists your recommendation first with a one-line rationale; "Other" is always available for custom overrides.**

Skip any theme that's clearly N/A for this project (e.g. skip e2e tooling for a library; skip CI gating if there's no CI).

Under `--auto`, do not ask any of the theme questions. Decide each applicable theme yourself using the same "recommendation first" logic, and record the choice with its one-line rationale in the drafted `testing.md`. Still produce a *real* strategy from the signals — override mode is never an excuse for a stub (see Output discipline).

### Themes to cover

1. **[QA] Test levels & pyramid** — which levels apply (unit / integration / e2e / contract / smoke), where the bulk of confidence comes from, rough ratio between levels.
2. **[QA] Coverage expectations** — the must-cover map: critical paths tied to specific PRD/goals sections; what's explicitly not covered and why; numeric coverage threshold (and tool) or explicitly "no numeric gate — the must-cover map is the bar".
3. **[SME] Frameworks & tooling** — runner, assertion library, mocking library, integration harness (e.g. Testcontainers vs in-memory vs embedded), e2e tool. Default order: architecture.md §12 Testing row → detected repo setup → stack-idiomatic pick. If the user's pick here contradicts architecture.md §12, surface the conflict and suggest `/pm:architect` (amend mode) to keep the two in sync — record the override either way.
4. **[SME] Fixtures, factories & test data** — factories vs static fixtures; seed/builder strategy; mock boundaries (what may be mocked vs what must be exercised for real); handling external services (stubs, record/replay, sandbox accounts).
5. **[QA] CI gating & flake policy** — which suites gate merges vs run nightly/manually; the canonical test command(s); runtime budget; flake quarantine/retry approach; parallelization.
6. **[QA] Out-of-scope testing** — testing concerns deliberately deferred this version (load/perf, chaos, mutation, visual regression, …) with a one-line why for each.

## Step 6 — Draft and confirm

Render the full `testing.md` to the user using the schema below. Allow per-section edits via free-form revisions. Iterate until the user confirms. Under `--auto`, skip the confirm-iterate loop and proceed straight to writing the file.

### `testing.md` schema

```markdown
---
slug: <slug>
version: <active_version>
created: <YYYY-MM-DD>
inherited_from: ""                             # set by /pm:version's copy step
status: drafted                                # drafted | locked | superseded
---

# Test strategy — <project title> <active_version>

## 1. Test levels & pyramid
<Which levels exist and where confidence comes from. One short paragraph + rough ratio.>

## 2. Coverage expectations
- Must cover: <critical paths, each tied to prd.md §N / goals.md §X>
- Explicitly uncovered: <list + one-line why each>
- Numeric threshold: <e.g. "80% line on new code via jacoco" or "none — the must-cover map is the bar">

## 3. Frameworks & tooling
| Level | Tool | Reason |
|---|---|---|
| Unit | <pick> | <one line> |
| Integration | <pick or N/A> | <one line> |
| E2E | <pick or N/A> | <one line> |
| Contract / other | <pick or N/A> | <one line> |

<If architecture.md exists: one line noting alignment with its §12 Testing row, or the recorded override.>

## 4. Fixtures & test data
- Factories/fixtures: <approach + tech>
- External services in tests: <stub / sandbox / record-replay, per service>
- Mock boundaries: <what may be mocked; what must be exercised for real>

## 5. CI gating
- Merge-gating suites: <which + canonical command(s), e.g. `mvn verify`>
- Non-gating (nightly/manual): <which, or none>
- Runtime budget: <target>
- Flake policy: <quarantine/retry approach>

## 6. Out of scope for <active_version>
<Testing concerns deliberately deferred, each with a one-line why.>

## 7. Open questions
<Anything that needs an answer before /pm:plan can shape criteria confidently.>

## Amendments

<!-- Append-only. Used by /pm:test "amend" mode and by /pm:version when carrying forward.
Format:

### YYYY-MM-DD — <short title>
**Why:** ...
**Change:** ...
-->
```

## Step 7 — Write the file

Write to `.pm/<slug>/<active_version>/testing.md`. If the file existed before (overwrite path), preserve nothing — the backup at `.bak.<timestamp>` is the historical record.

For the **amend** path: re-read the existing file, apply per-section changes the user described, and append a dated entry to `## Amendments` capturing the why and the change.

## Step 8 — Hand off

Print:
- Path written.
- Counts: levels in play; must-cover entries; merge-gating suites.
- Any open questions that came up — flag these as "answer before /pm:plan, or acceptance criteria will be vague."
- Next-step hint: `/pm:plan <slug>` (or `/pm:replan <slug>` if tasks already exist and the strategy changed).

## Output discipline

- This artifact is **optional** — never pressure the user into more strategy than the project needs. A thin testing.md is fine; an empty one is not. **Never write a stub** — a placeholder strategy creates false drift signal: the verifier treats `testing.md` as binding and would reject tasks that diverge from placeholder decisions. Either a real strategy or no file; no middle ground.
- Brownfield: extend the existing harness. Don't recommend a framework migration unless the user explicitly asks.
- Recommendations must be tied to the PRD / goals / research — especially `test-strategist.md` findings when present. Generic best-practice recommendations are weak; refer back to specific sections.
- Keep §3 consistent with architecture.md §12's Testing row. Surface conflicts to the user rather than silently diverging.
- "Other" is always a valid answer. The user's pick wins, period. Capture their rationale in the Reason column.
- Don't pad the file. Each section is a decision, not an essay. Bullets and short paragraphs.

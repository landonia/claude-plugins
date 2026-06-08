---
description: Generate ordered task files with frontmatter from the PRD and research, including dependencies and acceptance criteria.
model: opus
argument-hint: <slug>
---

# /pm:plan — Generate ordered tasks

You are running the `/pm:plan` command. Turn the PRD and research into an ordered list of executable task files.

## Inputs
- Slug: `$ARGUMENTS` (active-project resolution if empty).

## Step 1 — Resolve project and active version

Same resolution rules as other commands. Read `active_version` from `prd.md` frontmatter.

## Step 2 — Gate check

Required artifacts:
- `.pm/<slug>/prd.md` — REQUIRED. If missing, stop and tell the user to run `/pm:prd`.
- `.pm/<slug>/<active_version>/goals.md` — REQUIRED.
- `.pm/<slug>/<active_version>/research/` — RECOMMENDED. If empty or missing, warn: "No research found. Recommend running /pm:research <slug> first. Proceed anyway? (y/N)".
- `.pm/<slug>/<active_version>/architecture.md` — RECOMMENDED. If missing, warn: "No architecture decisions found. Recommend running /pm:architect <slug> first (decides stack and topology). Proceed anyway? (y/N)".
- `.pm/<slug>/<active_version>/testing.md` — OPTIONAL. If missing, print one informational line and continue without asking: "No test strategy found (optional). Run /pm:test <slug> to define one — otherwise tasks get test_refs: [] and tests follow repo conventions." Do NOT gate on it.

If `.pm/<slug>/<active_version>/tasks/` already has files, STOP and tell the user to use `/pm:replan <slug>` instead (which preserves done tasks).

## Step 3 — Read everything

Read:
- `prd.md` (including any Amendments)
- `<active_version>/goals.md`
- `<active_version>/architecture.md` (if present — including its Amendments)
- `<active_version>/testing.md` (if present — including its Amendments)
- Every file in `<active_version>/research/` (if present)

## Step 4 — Draft the task list

Decompose the work into atomic, executable tasks. Rules:
- Each task is **independently executable in one /pm:execute session** — typically a single concern, single layer, or single feature slice.
- Order tasks by execution sequence. Use `depends_on` for tasks that need a prior task to complete first.
- Use **3-digit zero-padded IDs** (`001`, `002`, …) — keeps files sorted alphabetically.
- Slugify the title for the filename: `001-set-up-postgres-schema.md`.
- Reference PRD/goals/research sections in `prd_refs` so the executor and verifier know what to read.
- Cite `architecture.md` sections in `arch_refs` when a task's implementation is driven by a specific architecture decision (queue tech, multi-tenancy model, API style, stack pick, etc.) — keeps the executor anchored to what's been decided.
- Cite `testing.md` sections in `test_refs` when a task's tests are governed by a specific strategy decision (must-cover map, tooling pick, fixture approach, CI gate); `[]` when there's no testing.md or no section applies. When testing.md is present, **shape acceptance criteria with it**: criteria for code tasks should name the test level and, where §5 specifies one, the suite/command that proves them (e.g. "covered by an integration test using Testcontainers per testing.md §3; `mvn verify` green"). Do NOT generate dedicated test-infrastructure tasks from testing.md — testing work lives inside the feature tasks it verifies.
- Acceptance criteria must be **observable** — something the verifier can check, not a vague aspiration.
- **Score each task's `complexity`** on the Fibonacci scale `1 | 2 | 3 | 5 | 8 | 13`, reflecting effort **and** uncertainty/risk (not just line count): `1` trivial / config-only · `2` small, single concern · `3` standard feature slice · `5` multi-file or non-trivial logic · `8` large, several moving parts · `13` very complex. A `13` is a hint that the task is too big — prefer splitting it into two smaller tasks. This score drives `/pm:status` version weight and the `/pm:gantt` chart.
- **Note parallelizable structure when obvious.** If a task has multiple independent sub-units (similar adapters across different APIs, several unrelated call sites, independent boilerplate files, etc.), call it out in `## Implementation notes` so the executor knows it's a candidate for parallel Agent subagent dispatch. This is advisory — the executor sees the actual code and makes the final call. Don't reach for it on tasks with sequential reasoning (schema → migration → code) or shared-file refactors.

Present the drafted list as a table to the user before writing files:

| ID  | Title                       | Pts | Depends on | Refs                       |
|-----|-----------------------------|-----|------------|----------------------------|
| 001 | Set up Postgres schema      | 3   | —          | goals.md §What ships, §3.1 |
| 002 | Auth endpoints              | 5   | 001        | prd.md §3.2                |
| ... |                             |     |            |                            |

Let the user edit (add/remove/reorder/rename) before writing. Use AskUserQuestion to confirm.

## Step 5 — Write task files

For each task, write `.pm/<slug>/<active_version>/tasks/<NNN>-<slug>.md` with this exact format:

```markdown
---
id: <NNN>
title: <Title>
status: pending          # pending | in-progress | done-pending-verify | done | rejected
assignee: ""             # set by /pm:claim — "<name> <email>"
branch: ""               # set by /pm:claim — pm/<slug>/<NNN>-<task-slug>
claimed_at: ""           # set by /pm:claim — YYYY-MM-DD
pr_url: ""               # set by /pm:complete — GitHub PR URL
completed_at: ""         # set by /pm:complete — YYYY-MM-DD
jira_key: ""             # set by /pm:jira-link or /pm:jira-create — e.g. "PROJ-123"
depends_on: []           # list of task ids as strings, e.g. ["001", "002"]
complexity: <N>          # Fibonacci points: 1 | 2 | 3 | 5 | 8 | 13 — relative effort/risk; drives /pm:status weight and /pm:gantt
prd_refs:                # list of section references
  - "prd.md §3.1"
  - "goals.md §What ships"
arch_refs:               # architecture.md sections that bind this task's design; [] if none
  - "architecture.md §3 Sync vs async work"
  - "architecture.md §12 Tech stack"
test_refs:               # testing.md sections that govern this task's tests; [] if none
  - "testing.md §2 Coverage expectations"
research_refs:           # research files that informed this task; [] if none
  - "research/security-architect.md §Findings 2"
acceptance_criteria:
  - <observable criterion 1>
  - <observable criterion 2>
created: <YYYY-MM-DD>
---

## Task
<2–6 sentence description of what to do and why. Reference the PRD/research where helpful.>

## Implementation notes
<Optional. Stack hints, specific files to touch, libraries to use, patterns to follow from research. Keep terse.>

## Out of scope
<Anything an executor might think falls into this task but doesn't. Prevents scope creep.>

## Verifier notes
<!-- Empty at creation. Populated by /pm:verify if rejected. -->
```

## Step 6 — Hand off

Print:
- Count of tasks written.
- The first ready task (no unmet deps).
- Next-step hint: `/pm:execute <slug>` (auto-picks the first ready task) or `/pm:next <slug>` to peek.
- If `.pm/<slug>/.jira.yml` exists (Jira is enabled for this project): also print `Tip: /pm:jira-create <slug>` so the user can batch-create Jira issues for the new tasks.

## Output discipline
- Don't generate more than ~25 tasks in one pass — if the work is bigger, group into phases and tell the user some tasks are "phase 2" placeholders that need their own decomposition later.
- A task is too big if its acceptance criteria can't be checked in one focused review. Split it. A task scored `complexity: 13` is usually too big — prefer splitting it into two 5s/8s.
- A task is too small if it's a one-line change with no testable surface — fold it into a sibling.
- Tasks should NOT cross version boundaries. If a thought belongs to v2, it goes in v2's plan, not v1's.

---
description: Generate ordered task files with frontmatter from the PRD and research, including dependencies and acceptance criteria.
argument-hint: <slug>
---

# /pm-plan — Generate ordered tasks

You are running the `/pm-plan` command. Turn the PRD and research into an ordered list of executable task files.

## Inputs
- Slug: `$ARGUMENTS` (active-project resolution if empty).

## Step 1 — Resolve project and active version

Same resolution rules as other commands. Read `active_version` from `prd.md` frontmatter.

## Step 2 — Gate check

Required artifacts:
- `.pm/<slug>/prd.md` — REQUIRED. If missing, stop and tell the user to run `/pm-prd`.
- `.pm/<slug>/<active_version>/goals.md` — REQUIRED.
- `.pm/<slug>/<active_version>/research/` — RECOMMENDED. If empty or missing, warn: "No research found. Recommend running /pm-research <slug> first. Proceed anyway? (y/N)".

If `.pm/<slug>/<active_version>/tasks/` already has files, STOP and tell the user to use `/pm-replan <slug>` instead (which preserves done tasks).

## Step 3 — Read everything

Read:
- `prd.md` (including any Amendments)
- `<active_version>/goals.md`
- Every file in `<active_version>/research/` (if present)

## Step 4 — Draft the task list

Decompose the work into atomic, executable tasks. Rules:
- Each task is **independently executable in one /pm-execute session** — typically a single concern, single layer, or single feature slice.
- Order tasks by execution sequence. Use `depends_on` for tasks that need a prior task to complete first.
- Use **3-digit zero-padded IDs** (`001`, `002`, …) — keeps files sorted alphabetically.
- Slugify the title for the filename: `001-set-up-postgres-schema.md`.
- Reference PRD/goals/research sections in `prd_refs` so the executor and verifier know what to read.
- Acceptance criteria must be **observable** — something the verifier can check, not a vague aspiration.

Present the drafted list as a table to the user before writing files:

| ID  | Title                       | Depends on | Refs                       |
|-----|-----------------------------|------------|----------------------------|
| 001 | Set up Postgres schema      | —          | goals.md §What ships, §3.1 |
| 002 | Auth endpoints              | 001        | prd.md §3.2                |
| ... |                             |            |                            |

Let the user edit (add/remove/reorder/rename) before writing. Use AskUserQuestion to confirm.

## Step 5 — Write task files

For each task, write `.pm/<slug>/<active_version>/tasks/<NNN>-<slug>.md` with this exact format:

```markdown
---
id: <NNN>
title: <Title>
status: pending          # pending | in-progress | done-pending-verify | done | rejected
depends_on: []           # list of task ids as strings, e.g. ["001", "002"]
prd_refs:                # list of section references
  - "prd.md §3.1"
  - "goals.md §What ships"
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
<!-- Empty at creation. Populated by /pm-verify if rejected. -->
```

## Step 6 — Hand off

Print:
- Count of tasks written.
- The first ready task (no unmet deps).
- Next-step hint: `/pm-execute <slug>` (auto-picks the first ready task) or `/pm-next <slug>` to peek.

## Output discipline
- Don't generate more than ~25 tasks in one pass — if the work is bigger, group into phases and tell the user some tasks are "phase 2" placeholders that need their own decomposition later.
- A task is too big if its acceptance criteria can't be checked in one focused review. Split it.
- A task is too small if it's a one-line change with no testable surface — fold it into a sibling.
- Tasks should NOT cross version boundaries. If a thought belongs to v2, it goes in v2's plan, not v1's.

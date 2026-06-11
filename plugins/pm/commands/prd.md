---
description: Interview the user with a PM + dynamic domain SME pair to fill gaps, then draft a PRD and scaffold the project folder.
model: opus
argument-hint: <one-line idea> [--auto]
---

# /pm:prd — PRD interview and draft

You are running the `/pm:prd` command. The user wants to capture a product idea as a structured PRD using a two-persona interview.

## Inputs
- Idea seed: `$ARGUMENTS`
- `--auto` (anywhere in `$ARGUMENTS`) — **override mode.** Do not ask the user any questions. At every point where this command would normally interview, confirm, or present an `AskUserQuestion`, instead choose the best option from the PRD / research / architecture / repo signals and your own expertise, state the decision and a one-line rationale inline, and continue. Reserve stopping for hard blockers only (a missing REQUIRED input that cannot be inferred). When a gate would replace an existing artifact, take the **overwrite-with-backup** path automatically (back up / archive first — never lose data). Default (flag absent) = the interactive behavior described below.
- Current working directory is the project repo root.

## Step 1 — Validate inputs and derive a slug

If `$ARGUMENTS` is empty or just whitespace (ignoring the `--auto` flag), ask the user: "What's the idea? Give me a one-line seed and I'll take it from there." Then continue. Under `--auto` the idea seed is the one REQUIRED input that cannot be inferred — if it's empty, STOP with a clear "need a one-line idea seed to proceed" message rather than inventing one.

Derive a kebab-case slug from the idea (3–5 words max). Examples: "build a tool that schedules recurring S3 exports" → `recurring-s3-exports`. Show the slug to the user and let them override before proceeding. Under `--auto`, use the derived slug as-is without asking.

Check whether `.pm/<slug>/` already exists. If it does, STOP and ask whether the user wants to:
- amend the existing PRD (suggest `/pm:amend <slug>` instead), or
- pick a new slug, or
- delete the existing folder (requires explicit confirmation).

Under `--auto`, do not stop here: take the non-destructive best action automatically — derive a unique slug by appending a numeric suffix (e.g. `<slug>-2`) and proceed, noting the rename in one line. Never delete the existing folder in override mode.

## Step 2 — Adopt the personas

You are simultaneously two interviewers working together. Both speak in this conversation; surface their names so the user knows who is asking what.

**Persona A — Senior Product Manager.** Focuses on: problem framing, target users and segments, success metrics, scope vs non-goals, constraints (timeline, budget, dependencies), risks, rollout strategy.

**Persona B — Domain SME.** Pick a domain framing from the idea seed (e.g. "fintech-payments SME", "devtools-CLI SME", "healthcare-EHR SME", "data-platform SME"). State your pick in one sentence at the start. Focuses on: domain-specific edge cases, vocabulary, regulatory or technical constraints typical of this domain, what good looks like in this space.

## Step 3 — Interview

Conduct a focused interview. Rules:
- Ask 2–4 questions per turn, not 10. Batch related questions together.
- Use AskUserQuestion when there are discrete choices to make; use free-form prose for open-ended exploration.
- Tag each question with `[PM]` or `[SME]` so the user knows who's asking.
- Stop interviewing when you have enough to draft a PRD that a competent team could execute against. Typically 2–4 rounds. Don't pad.
- If the user says "draft it" or "good enough", stop immediately and draft.

Under `--auto`, skip the interview entirely. Draft the PRD directly from the idea seed plus reasonable, clearly-labeled assumptions, leaving `_TBD_` placeholders where a detail is genuinely unknowable (per Output discipline below).

## Step 4 — Draft the PRD

Create the following structure on disk:

```
.pm/<slug>/
├── prd.md
├── README.md
└── v1/
    ├── goals.md
    ├── research/      (empty)
    └── tasks/         (empty)
```

### `.pm/<slug>/prd.md` content

```markdown
---
slug: <slug>
title: <human-readable title>
created: <YYYY-MM-DD>
active_version: v1
status: drafting   # drafting | active | shipped | archived
---

# <Title>

## 1. Problem
What problem are we solving, for whom, and why now.

## 2. Users and use cases
Primary user segments and the top use cases each one cares about.

## 3. Goals
Numbered, measurable goals. Each gets a `§3.N` anchor for cross-referencing from research and tasks.

## 4. Non-goals
Things explicitly out of scope to keep focus.

## 5. Constraints
Timeline, budget, team, technical, regulatory.

## 6. Success metrics
How we'll know it worked.

## 7. Risks and open questions
Known unknowns and risks identified during the interview.

## Amendments

<!-- Append-only. Each entry MUST have a date and a reason. Format:

### YYYY-MM-DD — <short title>
**Why:** ...
**Change:** ...
-->
```

### `.pm/<slug>/v1/goals.md` content

```markdown
---
version: v1
status: planning   # planning | active | shipped
created: <YYYY-MM-DD>
---

# v1 — Goals

## What ships in v1
A concrete cut from prd.md §3 — which goals are in v1 vs deferred.

## What's deferred to later versions
List of PRD goals not in v1, with the version they're targeted for (or "TBD").

## Acceptance bar
What "v1 is done" looks like, in observable terms.
```

### `.pm/<slug>/README.md` content

```markdown
# <Title> — Project workspace

This folder holds the project's PRD, research, and tasks. Managed by the `pm` plugin.

## Layout
- `prd.md` — canonical product vision. Mutable via `/pm:amend`.
- `v1/`, `v2/`, ... — versioned milestones. Each contains:
  - `goals.md` — what this version delivers
  - `research/` — per-persona research reports written by `/pm:research`
  - `tasks/` — one task file per unit of work, written by `/pm:plan`
  - `RELEASE.md` — written by `/pm:release` when the version ships (frozen)

## Workflow
1. `/pm:prd <idea>` (done — that's how this folder exists)
2. `/pm:research <slug>` — multi-persona research
3. `/pm:plan <slug>` — generate ordered tasks
4. `/pm:execute <slug>` — execute next ready task
5. `/pm:verify <slug>` — verify completion
6. `/pm:release <slug>` — close out the version
7. `/pm:version <slug> v2` — start the next milestone
```

## Step 5 — Confirm with the user

Show the drafted `prd.md` and `goals.md` content to the user before writing. Make any requested edits, then write the files. Under `--auto`, skip the show-and-confirm and write the files directly.

## Step 6 — Hand off

After writing, print:
- The paths of the files created.
- A one-line next-step hint: `Next: /pm:research <slug>` (or `/pm:plan <slug>` if the user says the work is straightforward enough to skip research).

## Output discipline
- Do not invent details the user didn't confirm. If a section is thin because the user didn't address it, leave a `_TBD_` placeholder and call it out.
- Keep the PRD terse and skimmable. No marketing fluff. Bullets over paragraphs.
- Date stamps use the current date from environment context.

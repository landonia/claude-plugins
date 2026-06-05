---
description: Fast-path planning for small projects — compressed PRD, one persona of light research, optional architecture gate, and 1–5 tasks in a single command. Produces the same on-disk artifacts as the full pipeline so all downstream commands work unchanged.
model: opus
argument-hint: <one-line idea>
---

# /pm:express — Fast-path planning for small projects

You are running the `/pm:express` command. The user wants to plan a **small project** — a single-purpose feature, a focused fix, or a one-shot prototype — without paying the cost of the full `/pm:prd` → `/pm:research` → `/pm:architect` → `/pm:plan` pipeline.

Express folds those four steps into one command with compressed input and minimal scaffolding. The on-disk artifacts you produce are the **same shape** the rest of the pipeline produces — `prd.md`, `goals.md`, optionally one research file, optionally tasks — so `/pm:claim`, `/pm:execute`, `/pm:verify`, `/pm:complete`, `/pm:handoff`, `/pm:resume`, and `/pm:replan` all work against express output unchanged.

If at any point the work clearly isn't small (scope cap fails, architecture decisions are non-trivial, the task count blows past five), surface that and offer the user the graduation path to the full pipeline. Express is a fast-path, not a corner-cutting tool.

## Inputs

- Idea seed: `$ARGUMENTS`
- Current working directory is the project repo root.

## Step 1 — Validate inputs and derive a slug

If `$ARGUMENTS` is empty or whitespace, ask: "What's the idea? Give me a one-line seed and I'll take it from there." Then continue.

Derive a kebab-case slug (3–5 words). Show it to the user; let them override.

Check `.pm/<slug>/`:
- **Doesn't exist** → proceed normally.
- **Exists with `prd.md` and `v1/goals.md` only (no research, no architecture, no tasks)** → assume this is an express run that was aborted by the architecture gate in Step 4; pick up from Step 3 (research) using the existing PRD. Tell the user: "Resuming express for <slug> — PRD and goals already on disk."
- **Exists with any other state** → STOP and offer: amend the existing PRD (`/pm:amend <slug>`), pick a new slug, or delete the existing folder (explicit confirmation required).

## Step 2 — Compressed PM interview

Adopt **one persona only**: Senior PM. No domain SME — SME-grade rigor is what `/pm:prd` is for; cloning it here defeats the speed goal.

Conduct a tight interview. Rules:
- Ask 2–4 questions per turn. Typically 1–2 rounds total.
- Use AskUserQuestion for discrete choices; free-form prose for open exploration.
- Cover only the load-bearing fields:
  - **Problem** — one paragraph: what's broken or missing, and why now.
  - **Users** — one line: who's affected.
  - **Success criteria** — 1–3 observable outcomes.
  - **Constraints** — only binding ones (deadline, must-not-break X, integration point Y). Skip generic "good code" wishes.
  - **Scope cap** — explicit confirmation: "Is this work you'd realistically expect to ship in 1–5 task-sized chunks?"

If the scope-cap answer reveals the work isn't small, surface it: *"This sounds larger than express targets. Continue express anyway, or run `/pm:prd <slug>` for the full PRD treatment?"* — let the user pick. If they continue, proceed with the same compression but flag in the hand-off that the project may need graduation later.

Skip the full PRD's `Non-goals`, `Risks and open questions`, and detailed rollout strategy. They're either obvious at this scope or unnecessary; the section headers will still exist in `prd.md` (Step 5) with one-line *"Not material at this scope"* placeholders to keep `prd_refs` section anchors (§4, §7) stable for downstream tooling.

## Step 3 — Light research (one persona, smart-picked)

Detect repo state at the working directory:
- **Brownfield** if any of: `pom.xml`, `build.gradle`, `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `Gemfile`, `*.csproj`, `Dockerfile` at the root.
- **Greenfield** otherwise (empty repo, or just a README).

**Default persona pick:**
- **Brownfield** → `existing-codebase-archaeologist`. This is always the highest-value persona for small work on an existing codebase: it surfaces patterns, conventions, and integration points the task must respect.
- **Greenfield** → smart-pick from PRD signals:
  - auth / billing / PII / PCI mentioned → `security-architect`
  - heavy data / schemas / migrations → `data-modeler`
  - user-facing UI / accessibility / flows → `ux-researcher`
  - third-party APIs / webhooks → `integration-engineer`
  - no clear signal → **skip research entirely** and proceed with `research_refs: []` on the tasks.

Present the pick to the user with **one AskUserQuestion** offering:
- Accept the recommended persona
- Swap to a different one (free-form via "Other" — name the persona slug)
- Skip research entirely

If a persona is selected, dispatch **one Agent subagent** with this prompt shape (mirrors `/pm:research`'s subagent prompt with the persona's brief from `plugins/pm/personas.md`):

> You are the `<persona-slug>` for a focused research pass on a small project. Read `.pm/<slug>/prd.md` and `.pm/<slug>/v1/goals.md` in full. Write `.pm/<slug>/v1/research/<persona-slug>.md` with the standard sections: Summary (2–4 bullets), Findings (numbered, each citing `prd.md §N` or `goals.md §X`), Gotchas, Recommendations, Open questions for the user, Out of scope. Keep the whole report under ~800 words — this is a small project. Do not invent scope; if a section has nothing material to say, write "None material at this scope."

**No `_index.md`.** With one persona there's nothing to index; the task's `research_refs` will point directly at the persona file.

If the persona's `Open questions for the user` surfaces something that materially changes scope (the problem statement, the success criteria, a major constraint), STOP planning and offer `/pm:amend <slug>` to capture the change before continuing. For a true small project this should be rare.

## Step 4 — Architecture gate

**Brownfield:** Skip architecture.md entirely. Tasks will get `arch_refs: []`. In Step 5, `goals.md` gets a one-line callout: *"Architecture: inherits existing repo conventions; run `/pm:architect` if scope expands to introduce new stack components."*

**Greenfield with obvious stack** (CLI tool, single-file script, learning project, tiny utility): skip architecture silently. Same `arch_refs: []` and same callout.

**Greenfield with non-trivial stack signals** — any of:
- multi-tenancy mentioned (SaaS / multi-org / per-tenant)
- distributed system / multiple services
- real-time / streaming / pub-sub
- auth + billing + data + UI all in scope (full SaaS-shape)
- the user explicitly mentioned a stack-level decision they want help with

→ Ask **one consolidated question** via AskUserQuestion:

> "This looks like a greenfield project with non-trivial stack choices (e.g. auth model, primary data store, deployment topology). Architecture decisions bind every downstream task and the verifier rejects drift. Run `/pm:architect <slug>` first? (recommended)"

- **Yes → recommended:** STOP planning. Print:
  ```
  PRD and goals saved at .pm/<slug>/. Run /pm:architect <slug>, then re-run /pm:express <slug> to continue.
  ```
  Make sure `prd.md` and `v1/goals.md` are written to disk before stopping (do Step 5's PRD/goals write portion first, defer task generation). On re-entry, Step 1's collision detection sees the existing partial state and resumes from Step 3.

- **No → user accepts deferred decisions:** proceed with `arch_refs: []` and the same callout. The user has explicitly chosen to defer.

**Never write a stub `architecture.md`.** A partial or placeholder architecture file creates false drift signal — the verifier treats `architecture.md` as binding and would reject tasks that diverge from placeholder decisions. Either real architecture (via `/pm:architect`) or no architecture (with `arch_refs: []`); no middle ground.

## Step 5 — Scaffold and draft PRD + goals

Create on disk (same layout as `/pm:prd`):

```
.pm/<slug>/
├── prd.md
├── README.md
└── v1/
    ├── goals.md
    ├── research/      (contains the one persona file from Step 3, if any)
    └── tasks/         (empty until Step 6)
```

### `.pm/<slug>/prd.md` content

Use the same frontmatter and section structure as `/pm:prd` — section numbering stays stable so any code/tooling that anchors on `prd.md §3.2` keeps working. Body content is compact:

```markdown
---
slug: <slug>
title: <human-readable title>
created: <YYYY-MM-DD>
active_version: v1
status: drafting   # drafting | active | shipped | archived
express: true      # marker: this PRD was produced by /pm:express
---

# <Title>

## 1. Problem
<one paragraph from the interview>

## 2. Users and use cases
<one or two lines>

## 3. Goals
<numbered, 1–3 entries. Each gets §3.N anchor.>

## 4. Non-goals
_Not material at this scope. Run `/pm:prd <slug>` if scope grows._

## 5. Constraints
<bulleted list of binding constraints, or "_None binding at this scope._">

## 6. Success metrics
<bulleted list, 1–3 entries — same items as Goals if metrics ARE the goals>

## 7. Risks and open questions
_Not material at this scope. Run `/pm:prd <slug>` if risks emerge._

## Amendments

<!-- Append-only. Each entry MUST have a date and a reason. Format:

### YYYY-MM-DD — <short title>
**Why:** ...
**Change:** ...
-->
```

The `express: true` frontmatter flag is informational — it lets `/pm:status`, `/pm:list`, and graduation commands (`/pm:research`, `/pm:architect`, `/pm:replan`) recognize an express-produced project and tailor their messaging. None of the commands need to be changed today to read this flag; it's there for future tooling.

### `.pm/<slug>/v1/goals.md` content

```markdown
---
version: v1
status: planning   # planning | active | shipped
created: <YYYY-MM-DD>
---

# v1 — Goals

## What ships in v1
<bulleted cut from prd.md §3 — all of them, since express scope is small>

## What's deferred to later versions
_None at this scope. Add later if scope grows (`/pm:amend`)._

## Acceptance bar
<what "done" looks like in observable terms — 2–4 bullets>

## Architecture
_<one-line callout based on Step 4 outcome>_

<!-- Examples:
Inherits existing repo conventions. Run `/pm:architect` if scope expands to introduce new stack components.

OR

Stack decisions deferred — user opted to proceed without /pm:architect. Run `/pm:architect` before adding tasks that depend on stack-level decisions.

OR (only if /pm:architect was run separately and architecture.md exists)
See `architecture.md` for binding decisions.
-->
```

### `.pm/<slug>/README.md` content

Same as `/pm:prd`'s README, but the Workflow section reflects the express path:

```markdown
# <Title> — Project workspace

This folder holds the project's PRD, research, and tasks. Managed by the `pm` plugin.
Created via `/pm:express` — fast-path planning for small projects.

## Layout
- `prd.md` — canonical product vision. Mutable via `/pm:amend`.
- `v1/`, `v2/`, ... — versioned milestones. Each contains:
  - `goals.md` — what this version delivers
  - `research/` — per-persona research reports
  - `tasks/` — one task file per unit of work
  - `RELEASE.md` — written by `/pm:release` when the version ships (frozen)

## Workflow
1. `/pm:express <idea>` (done — that's how this folder exists)
2. `/pm:claim <slug>` — claim the first task
3. `/pm:execute <slug>` — execute next ready task
4. `/pm:verify <slug>` — verify completion
5. `/pm:complete <slug>` — open the PR
6. `/pm:release <slug>` — close out the version

## Graduating from express
If scope grew beyond what express handles:
- `/pm:research <slug>` — add more research personas (additive — keeps the existing file)
- `/pm:architect <slug>` — capture architecture decisions
- `/pm:replan <slug>` — regenerate pending tasks against the new artifacts
```

Show the drafted `prd.md` and `goals.md` to the user, fold in any edits, then write all three files.

## Step 6 — Compressed task generation

Decompose the work into **1–5 tasks**, biased toward fewer/larger. Rules:
- Each task is independently executable in one `/pm:execute` session.
- Only split when truly atomic (different files, different acceptance criteria, real dependency between them).
- Order by execution sequence; use `depends_on` for any prerequisite chain.
- 3-digit zero-padded IDs (`001`, `002`, …).
- `arch_refs: []` (express doesn't produce binding architecture).
- `research_refs`: point at the one persona file from Step 3 with specific section refs, or `[]` if research was skipped.
- Acceptance criteria must be **observable** — something the verifier can check.
- **Note parallelizable structure when obvious.** If a task has multiple independent sub-units (similar adapters, unrelated call sites, independent boilerplate), call it out in `## Implementation notes` so the executor knows it's a candidate for parallel Agent subagent dispatch. Advisory — the executor makes the final call.

**Soft cap of 5 tasks.** If your draft needs more than 5, surface it:

> "Express targets 1–5 tasks; this scope needs <N>. Continue express with <N> tasks anyway, or graduate to `/pm:plan <slug>` for the full task-table review?"

Don't silently exceed the cap. If the user picks graduation, write the PRD/goals/research from Steps 5 and 3 (if not already written), then exit with a hand-off pointing at `/pm:plan`.

Present the drafted task list as a table before writing files:

| ID  | Title                       | Depends on | Refs                       |
|-----|-----------------------------|------------|----------------------------|
| 001 | <task title>                | —          | goals.md §What ships, §3.1 |
| 002 | <task title>                | 001        | prd.md §3.2                |

Let the user edit (add/remove/rename/reorder) before writing. Use AskUserQuestion to confirm.

Write each task file to `.pm/<slug>/v1/tasks/<NNN>-<task-slug>.md` using the exact same frontmatter and body shape as `/pm:plan` (see `/pm:plan` Step 5 for the canonical format) — frontmatter fields, status lifecycle, body sections (`## Task`, `## Implementation notes`, `## Out of scope`, `## Verifier notes` placeholder). Do not invent new task-frontmatter fields; downstream commands read the same schema.

## Step 7 — Hand off

Print a summary tailored to what was actually produced:

```
Express planning done for <slug>.
  PRD:           .pm/<slug>/prd.md
  Goals:         .pm/<slug>/v1/goals.md
  Research:      <path to the persona file, or "(skipped)">
  Architecture:  <"(deferred — inherits existing repo conventions)" or "(deferred — user opted to proceed without /pm:architect)" or "(scope is greenfield-trivial)">
  Tasks:         <N> task(s) in .pm/<slug>/v1/tasks/

First ready task: <NNN> — <title>

Next: /pm:claim <slug>     (recommended for teams — makes the claim visible via git)
   or /pm:execute <slug>   (solo, jumps straight in)

If scope grows: /pm:research <slug>, /pm:architect <slug>, /pm:replan <slug>.
```

If `.pm/<slug>/.jira.yml` exists (Jira is enabled for this project), also print: `Tip: /pm:jira-create <slug>` so the user can batch-create Jira issues for the new tasks.

## Output discipline

- **Don't invent details the user didn't confirm.** Thin sections in the PRD get `_Not material at this scope._` placeholders, not made-up content.
- **Don't write a stub `architecture.md`.** Architecture is either real (via `/pm:architect`) or absent with `arch_refs: []`. No middle ground.
- **Respect the scope cap.** If the interview reveals the work isn't small, or task draft exceeds 5, offer graduation rather than silently exceeding.
- **One persona for research, max.** Multi-persona dispatch is what `/pm:research` is for. Express picks one or zero.
- **Don't auto-run `/pm:claim` or `/pm:execute`.** Planning and executing are separate steps so the user can pause between them.
- **Date stamps use the current date from environment context.**
- **The artifact contract is non-negotiable.** Task frontmatter, prd.md frontmatter, goals.md frontmatter — every field name and section header matches the canonical pipeline. Downstream commands read these as schemas, not suggestions.

# pm — Project management pipeline for Claude Code

A set of slash commands that take a project from a one-line idea, through structured PRD interview, multi-persona research, ordered task generation, stack-aware execution, and independent verification — with first-class support for versioned milestones (v1, v2, ...).

Designed for large and complex projects where you want the planning and execution loop to be **rigorous, auditable, and persistent on disk** rather than living in chat history.

---

## Install

From this marketplace:

```
/plugin marketplace add landonia/claude-plugins
/plugin install pm@landonia-plugins
```

All commands are namespaced under the plugin — invoke them as `/pm:<command>` (e.g. `/pm:prd`, `/pm:execute`). The `pm:` prefix prevents collisions with other plugins.

> **Note on commands vs skills.** Pm ships its commands as flat `commands/*.md` files. After Claude Code merged custom commands into the skills system ([docs](https://code.claude.com/docs/en/skills.md)), commands appear in the unified "available skills" list — but they are still commands, not skill directories, and the flat layout is fully supported. The flat form is preferred for user-invoked commands like these (every pm command is typed with arguments, e.g. `/pm:claim 003`).

---

## Mental model

Every project lives under `.pm/<project-slug>/` in your repo. The folder is committable, portable, and human-readable.

```
.pm/<slug>/
├── prd.md              # canonical product vision; append-only Amendments section
├── README.md           # auto-generated folder explainer
├── v1/
│   ├── goals.md        # what v1 delivers (cut from PRD)
│   ├── architecture.md # architecture + tech-stack decisions for v1
│   ├── testing.md      # test strategy for v1 (optional)
│   ├── research/
│   │   ├── _index.md
│   │   ├── security-architect.md
│   │   └── data-modeler.md
│   ├── tasks/
│   │   ├── 001-set-up-schema.md
│   │   └── 002-auth-endpoints.md
│   └── RELEASE.md      # written when v1 ships; frozen
└── v2/
    ├── goals.md
    ├── architecture.md # carried forward from v1, amended for v2
    ├── testing.md      # carried forward from v1 (optional)
    ├── research/
    └── tasks/
```

Each task file is markdown with YAML frontmatter capturing `status`, `depends_on`, `complexity` (a Fibonacci effort/risk score — `1,2,3,5,8,13`), `prd_refs`, and `acceptance_criteria`. Status flows: `pending → in-progress → done-pending-verify → done` (or `→ rejected → pending` on a verify rejection). The `complexity` score drives version weight in `/pm:status` and the `/pm:gantt` chart.

### The flow

```
/pm:prd  →  /pm:research  →  /pm:architect  →  (/pm:test)  →  /pm:plan  ─┐
                                                                         ├→  /pm:claim  →  /pm:execute  →  /pm:verify  →  /pm:complete
/pm:express   (fast-path for small projects)  ───────────────────────────┤                     ▲       ▲          │              │
/pm:autoplan  (autonomous: runs the five above, each --auto)  ───────────┘                     │       │          ▼              ▼
                                                                                           /pm:resume  │     (rejected)    PR opened, merge
                                                                                                       │                          │
                                                                                                   /pm:handoff                    │
   /pm:amend  ──→  /pm:replan                                                                               /pm:release  →  /pm:version v2
```

`/pm:architect` consolidates the research into concrete architecture and tech-stack decisions (the file `architecture.md` is then read by `/pm:plan`, `/pm:execute`, and `/pm:verify` as the source of truth). `/pm:test` (optional) captures a per-version test strategy in `testing.md`; when present it shapes `/pm:plan`'s acceptance criteria and is binding on `/pm:execute` and `/pm:verify` — when absent, nothing changes. `/pm:claim` is optional for solo work and recommended for multi-developer teams — it makes your "I'm working on this" visible to teammates via git so two people don't double-implement the same task. `/pm:complete` opens the PR after `/pm:verify` accepts, and `/pm:resume` brings you back to a task's branch when you need to (e.g. PR feedback). `/pm:handoff` captures mid-task context when you need to stop before a task is done, so the next session (yourself later, or a teammate) can pick up without re-deriving where you left off. You can skip stages (`/pm:plan` will warn if there's no research or architecture but proceed) — the structure is opinionated, not rigid.

`/pm:auto` wraps the execute → verify pair in an autonomous loop — each phase runs in an isolated subagent with a fresh context, state lives in the task files — until no ready tasks remain. You still run `/pm:complete` per task and `/pm:release` at the end.

Each authoring command (`/pm:prd`, `/pm:research`, `/pm:architect`, `/pm:test`, `/pm:plan`) accepts an `--auto` flag: instead of interviewing you, the command makes the best decision at every point it would normally ask — stating each choice with a one-line rationale — and proceeds (hard blockers like a missing idea seed still stop). `/pm:autoplan` is the planning-phase sibling of `/pm:auto`: it runs that whole pipeline end to end, `prd → research → architect → test → plan`, **each stage in its own isolated `--auto` subagent**, then hands off to `/pm:auto`. Together they form a fully autonomous flow — **idea → tasks (`/pm:autoplan`) → done (`/pm:auto`)**. Unlike `/pm:express` (a compressed single-context fast path for *small* work), `/pm:autoplan` runs the full-rigor pipeline — the real two-persona PRD, real multi-persona research, full architecture and test strategy — with no human in the loop.

`/pm:express` is the sanctioned fast path for **small projects** — a single-purpose feature, a focused fix, a one-shot prototype. One command runs a compressed PRD interview (PM persona only), picks one research persona if useful, lets you defer architecture if it's not strictly necessary, and generates 1–5 tasks. The artifacts it writes are the same shape the full pipeline produces, so `/pm:claim`, `/pm:execute`, `/pm:verify`, `/pm:complete`, and `/pm:handoff` work against express output unchanged. If scope grows later, graduate by running `/pm:research`, `/pm:architect`, and `/pm:replan` in place.

*Optional: if Jira is enabled for the project (via `/pm:jira-init`), the same flow also pushes status to your Jira board — `/pm:claim` moves the linked issue to In Progress, `/pm:verify` to In Review, `/pm:complete` adds the PR URL as a comment, `/pm:version` creates a per-version epic, and `/pm:release` closes it. See [Jira integration](#jira-integration-optional) below.*

---

## Commands

### Project lifecycle

#### `/pm:prd <one-line idea>`
Two personas — a Senior PM and a dynamically-picked domain SME — interview you to fill gaps, then draft `prd.md` and scaffold `v1/`.

```
/pm:prd "build a tool that lets users schedule recurring exports to S3"
```

You'll get tagged questions like `[PM] Who are the primary users — engineers running ad-hoc exports, or ops teams setting up scheduled pipelines?` and `[SME-data-platform] What data sources are in scope — S3, RDS, warehouses, or all of the above?` After 2–4 rounds, the PRD is drafted and shown to you for edits before writing.

#### `/pm:express "<one-line idea>"`
Fast-path planning for small projects, all in one command. Compressed PM interview (no domain SME), one light research persona (smart-picked: codebase-archaeologist on brownfield, PRD-signal pick on greenfield, or skipped entirely), architecture deferred unless the project is greenfield with non-trivial stack signals, and 1–5 tasks biased toward fewer/larger.

```
/pm:express "add a /pm:metrics command that prints tokens consumed per command"
/pm:express "tiny CLI that prints today's weather from a public API"
```

Use it when the work is a single-purpose feature or a focused fix that you'd realistically expect to ship in 1–5 task-sized chunks. Express writes the same files the full pipeline does — `prd.md`, `v1/goals.md`, optionally `v1/research/<persona>.md`, and task files — so `/pm:claim`, `/pm:execute`, `/pm:verify`, `/pm:complete`, `/pm:handoff`, and `/pm:resume` all work against express output unchanged. The PRD frontmatter carries an `express: true` marker so the project's origin is visible.

Tasks generated by express have `arch_refs: []` and `test_refs: []` (express doesn't write `architecture.md` or `testing.md`), so the verifier's architecture- and test-strategy-drift checks are bypassed cleanly — no stub or placeholder files are ever written.

**Safety gates:** If the scope-cap question reveals the work isn't small, express asks whether to continue or graduate to `/pm:prd`. If the task draft would exceed 5, it surfaces a graduation option to `/pm:plan`. On greenfield projects with non-trivial stack signals (multi-tenancy, distributed, real-time, full SaaS), it stops and recommends running `/pm:architect` first.

**Graduation:** If express turns out to be insufficient (scope grew, architecture decisions surfaced, more research is needed), run the corresponding full-pipeline commands in place: `/pm:research <slug>` adds more personas additively, `/pm:architect <slug>` runs the architecture interview from scratch, `/pm:test <slug>` captures a binding test strategy, and `/pm:replan <slug>` regenerates pending tasks against the new artifacts while preserving anything already done or in flight.

#### `/pm:amend <slug>`
Append a dated, append-only amendment to the PRD. Use after research surfaces something that changes scope, or when stakeholders shift requirements mid-flight.

```
/pm:amend recurring-s3-exports
```

The PRD's original body stays intact; the amendment is recorded under `## Amendments` with a `Why:`, `Change:`, and `Impact on pending work:` line. If you say "yes, this affects pending tasks", you'll be pointed at `/pm:replan` next.

---

### Research

#### `/pm:research [slug]`
Reads the PRD and active version's `goals.md`, picks 3–6 personas from the catalog (`plugins/pm/personas.md`) — security architect, data modeler, UX researcher, SRE, integration engineer, performance engineer, accessibility specialist, compliance/legal, test strategist, migration strategist, and the existing-codebase archaeologist for brownfield repos — then dispatches them as **parallel Agent subagents**. Each writes its own report referencing PRD/goals sections.

```
/pm:research recurring-s3-exports
```

You confirm the persona picks (with the option to add/remove) before dispatch. After all subagents return, an `_index.md` rolls up cross-cutting open questions. If those questions materially change scope, you'll be prompted to `/pm:amend`.

#### `/pm:rerun-research <slug> <persona-slug>`
Re-runs a single persona — useful when a PRD amendment invalidates one report, or when a persona's first pass was thin. The prior report is archived to `research/.archive/` so nothing is lost.

```
/pm:rerun-research recurring-s3-exports security-architect
```

---

### Architecture, tech stack & test strategy

#### `/pm:architect [slug]`
A two-persona interview — **Principal Architect** + a dynamically-picked **`<Stack> SME`** (e.g. "Java/Spring SME", "TypeScript/Node SME") — that consolidates the PRD and research into concrete architecture decisions and tech-stack picks. Output is `.pm/<slug>/<active_version>/architecture.md` and it becomes the source of truth that `/pm:plan`, `/pm:execute`, and `/pm:verify` read.

```
/pm:architect recurring-s3-exports
```

The interview is themed: deployment topology, scaling model (horizontal scaling, stateless instances), sync vs async work and queue tech, multi-tenancy model (if applicable), data layer, API style, real-time/streaming, consistency & resilience, identity & auth, observability, environments & deployment, plus a full tech-stack pass (language, framework, DB, cache, queue, jobs, auth provider, hosting, CI/CD, testing, build, log/metric/trace tools) and cross-cutting concerns (security baseline, i18n, accessibility, data retention, cost ceiling).

For every multiple-choice question you get a recommendation tied to the PRD and research; **"Other" is always available** to substitute anything you prefer. Brownfield repos pre-fill the existing stack as the default. Re-running the command on an existing project offers an **amend** path that only revisits sections you want to change — decisions append to the `## Amendments` section.

`/pm:execute` reads `architecture.md` before writing any code and refuses to silently substitute (e.g. picking Mongo when the file says Postgres). `/pm:verify` rejects implementations that drift from documented decisions, citing the specific violated section.

#### `/pm:test [slug]`
An **optional** two-persona interview — **QA Lead** + a dynamically-picked **`<Stack> Test SME`** — that decides the test strategy for the version: test levels and pyramid, the must-cover map (tied to PRD/goals sections), frameworks and tooling (defaulting from `architecture.md`'s Testing pick and the repo's detected test setup), fixtures and test data, CI gating and flake policy, and what's deliberately out of scope. Output is `.pm/<slug>/<active_version>/testing.md`.

```
/pm:test recurring-s3-exports
```

Like `/pm:architect`, every multiple-choice question leads with a recommendation tied to the PRD and research (the `test-strategist` research report, if present, seeds the defaults), **"Other" is always available**, brownfield repos pre-fill the existing test harness, and re-running offers an **amend** path that appends to `## Amendments`.

The strategy is **presence-gated binding**: skip the command and nothing changes anywhere. Run it, and `/pm:plan` shapes acceptance criteria around it (tasks get `test_refs`), `/pm:execute` writes tests at the documented levels with the documented tooling, and `/pm:verify` rejects test drift — unless the executor documents a justified deviation in the Implementation summary, which passes with a note.

---

### Planning

#### `/pm:plan [slug]`
Turns PRD + research + architecture into ordered task files. Each task is atomic, executable in one `/pm:execute` session, and includes acceptance criteria the verifier can check. Dependencies are declared explicitly so `/pm:execute` can auto-pick the next ready task. Tasks that hinge on a specific architecture decision get `arch_refs` so the executor stays anchored. Tasks whose tests are governed by `testing.md` get `test_refs`; without a `testing.md` every task carries `test_refs: []` and tests follow repo conventions.

```
/pm:plan recurring-s3-exports
```

You see the full task list as a table before any files are written, and you can edit (add/remove/reorder/rename) before committing. Each task file gets a 3-digit zero-padded id (`001`, `002`, …) so they sort naturally.

#### `/pm:replan [slug]`
Regenerates pending/rejected tasks from the (possibly amended) PRD while **preserving** anything that's `done`, `done-pending-verify`, or `in-progress`. Replaced tasks are archived to `tasks/.archive/` rather than deleted.

```
/pm:replan recurring-s3-exports
```

Shown as a diff: `Preserving 3 / Replacing 2 / Adding 4` so you can confirm before files change.

---

### Execution and verification

#### `/pm:claim [slug] [task-id]`
Claims a task in a multi-developer setting. Creates the branch (`pm/<slug>/<NNN>-<task-slug>`), flips the task's `status` to `in-progress`, sets `assignee` from your git config, and commits + pushes immediately so the claim is visible to teammates. Optional in solo work, recommended on teams.

```
/pm:claim usage-billing                    # auto-picks next ready task
/pm:claim usage-billing 003                # claims a specific task
/pm:claim usage-billing 003 --force        # take over someone else's claim (handoff)
```

Pre-flight refuses if your working tree is dirty, your git identity isn't configured, or no remote exists. Pulls `main` (or current base) before reading task state so stale claims don't race. Refuses if the task is already claimed by someone else unless you pass `--force`.

#### `/pm:execute [slug] [task-id]`
The specialist coding agent. Runs in your main thread so you can intervene mid-task. Detects your stack (pom.xml, package.json, pyproject.toml, etc.) and triggers any relevant skills (e.g. `java-guidelines`, `frontend-design`) and reads any `CLAUDE.md` files. Reads the task, the PRD sections it references, and the relevant research files before writing a single line of code.

```
/pm:execute recurring-s3-exports         # auto-picks lowest-id ready task
/pm:execute recurring-s3-exports 003     # forces task 003 (warns if deps unmet)
```

Status transitions: flips to `in-progress` when work starts, `done-pending-verify` when complete. Appends an `## Implementation summary` to the task body listing files changed, criterion-by-criterion satisfaction with `file:line` evidence, and notes for the verifier.

When a task has independent sub-units (multiple similar adapters, unrelated call sites, separate boilerplate files), the executor dispatches them as **parallel Agent subagents in a single message** rather than implementing serially — a meaningful speedup on suitably-shaped work. The decision is the executor's: planning commands can flag obvious parallelism in the task's `## Implementation notes`, but the executor sees the actual code and chooses. Serial reasoning chains (schema → migration → code) and shared-file refactors stay serial; parallel dispatch only fires when independence is genuinely obvious. The Implementation summary lists which subagents ran so the verifier and PR reviewer can see the breakdown.

Honors claims: if you `/pm:execute` a task someone else has claimed, the command refuses unless you pass `--force` (the safe default in teams). Use `/pm:claim ... --force` to take over the claim cleanly, or `/pm:execute ... --force` to bypass the check if you've coordinated out-of-band.

If a previously rejected task is picked up, the executor reads the existing `## Verifier notes` and addresses each gap, then writes a `## Re-execution notes` section explaining how. If the task body contains `## Handoff notes` from a prior mid-task pause, the executor reads those too and uses them as advisory context (not binding like verifier notes) — see `/pm:handoff` below.

#### `/pm:handoff [slug] [task-id]`
Pauses an in-progress task and writes a handoff note onto the task file so the next session — yourself later, or a teammate — can pick up without re-deriving where you left off. The handoff captures only the **ephemeral, in-flight context** that isn't anywhere else: approach taken so far, what's committed vs uncommitted, concrete next steps, and gotchas surfaced during implementation that no planning document anticipated. It does NOT repeat the PRD, research, or architecture — those are already on disk and re-read by the next `/pm:execute`.

```
/pm:handoff usage-billing                  # auto-picks your current in-progress task
/pm:handoff usage-billing 003              # handoff a specific task
```

Refuses if the task isn't `in-progress` (handoffs only apply to active work), if you're on the wrong branch (run `/pm:resume` first), or if there's no remote (the handoff has to be visible). The command synthesises a draft from your current session, shows it to you for review/edit before writing, then commits and pushes **just the task file** — your uncommitted implementation changes stay in the working tree by design (they're what the handoff describes; the next executor inherits them via the branch state).

Status stays `in-progress` and the assignee/branch are unchanged — a handoff is **context-passing, not ownership transfer**. To actually hand the work to a teammate, they run `/pm:claim <slug> <NNN> --force` from their machine to take over the claim cleanly; the handoff notes are already on the branch waiting for them.

The next `/pm:execute` automatically picks up handoff notes as part of normal task body reading — no flag required.

#### `/pm:verify [slug] [task-id]`
A Senior QA / Tech Lead persona that **independently** verifies the work. Reads the PRD, research, task, and the actual diff (`git status` / `git diff`). Runs tests if the implementation summary specifies a command. Judges each acceptance criterion as PASS / FAIL / PARTIAL / UNVERIFIABLE with evidence.

```
/pm:verify recurring-s3-exports          # auto-picks lowest-id done-pending-verify task
/pm:verify recurring-s3-exports 003      # verify a specific task
```

On accept: status `done`, brief accepted note appended.
On reject: status `rejected`, plus a `## Verifier notes` section listing **specific, actionable gaps** so the next `/pm:execute` (which may be a different session entirely) can pick up cold and finish the work correctly.

#### `/pm:auto [slug] [--max-retries N] [--parallel [N]]`
Autonomously loops the execute → verify pair until no ready tasks remain. Each phase — every execute, every verify, every retry — runs in its own **isolated subagent with a fresh context**: the orchestrator just picks the next task, dispatches a worker, re-reads the task's status from disk (it never trusts the subagent's report), and decides whether to continue. State lives entirely in the task files, never in conversation context, so the verifier-independence guarantee survives automation — a verify subagent never shares context with the executor that produced the work, and a retry after rejection learns what went wrong solely from the `## Verifier notes` on disk.

```
/pm:auto usage-billing                   # run until no ready tasks remain (sequential — the default)
/pm:auto usage-billing --max-retries 3   # allow 3 rejections of the same task before stopping
/pm:auto usage-billing --parallel        # run independent tasks concurrently (default 3 at a time)
/pm:auto usage-billing --parallel 5      # up to 5 task pipelines at once (capped by the dep graph's width)
```

The loop: verify any `done-pending-verify` backlog first, then execute the lowest-id ready task → verify it. ACCEPT → next ready task. REJECT → re-execute the same task. It stops and hands back to you on: all tasks done (suggests `/pm:release`), the same task rejected `--max-retries` times (default 2 — prints the verifier notes verbatim), an executor blocker (prints the `## Blocker` verbatim), or no eligible tasks left (e.g. everything remaining is claimed by teammates). A final summary lists completed, rejection-capped, skipped-claimed, and blocked tasks.

**Parallel mode (`--parallel [N]`, opt-in; sequential is the default).** Runs up to N independent task pipelines (those whose `depends_on` are all done) concurrently. To do this safely it gives each task its **own git worktree** and the execute worker **commits to a per-task branch** so the independent verifier can review it cold; on ACCEPT the work is **merged back into your current branch** (serialized) so dependents see it. Merge conflicts between concurrently-completed tasks are auto-resolved, then the merged result is re-verified; an unresolvable merge or a failed re-verify leaves that task's branch for you to integrate by hand. Because this **commits to your current branch**, run it on a feature branch, not `main` (it warns if you don't). A per-task failure doesn't halt the run — in-flight work drains and the summary reports every outcome (completed, blocked, rejection-capped, anomalies, merge-failed, unreachable). Parallel mode requires the Workflow tool; without it the flag degrades to the sequential loop.

What auto does NOT do: it never runs `/pm:claim`, `/pm:complete`, or `/pm:release`, never passes `--force`, never pushes, and skips tasks claimed by someone else rather than taking them over. In **sequential** (default) mode it also never commits; **`--parallel` mode** is the one exception — it commits accepted work to per-task branches and to your current branch (but still never pushes or opens PRs). In multi-dev settings, `/pm:claim` before `/pm:auto` is still the recommended courtesy.

#### `/pm:autoplan <one-line idea> | <slug> [--force]`
The planning-phase sibling of `/pm:auto`: runs the full authoring pipeline — `prd → research → architect → test → plan` — autonomously, with **each stage in its own isolated subagent** invoking the real command with `--auto`. State lives on disk; the orchestrator only sequences stages and re-confirms each stage's artifact on disk before moving on (it never trusts the worker's report). When the last stage lands task files, it hands off to `/pm:auto <slug>`.

```
/pm:autoplan "build a tool that schedules recurring exports to S3"   # idea → ready-to-execute tasks
/pm:autoplan recurring-s3-exports                                    # resume: run only the stages still missing
/pm:autoplan recurring-s3-exports --force                           # re-run stages whose artifacts already exist
```

Pass a **one-line idea** to start a fresh project (the `prd` stage derives the slug), or an **existing slug** to resume — autoplan skips any stage whose artifact is already on disk and runs the rest (`--force` re-runs present stages, each via its command's overwrite-with-backup path). It stops and hands back on: all stages done (suggests `/pm:auto`), nothing left to author (resume where everything already exists), a PRD hard blocker (no idea seed), or an anomaly (a stage ran but its expected artifact didn't appear — names the stage). Like `/pm:auto`, the loop runs as a deterministic Workflow with an in-context fallback, and the research stage dispatches its own persona subagents in parallel beneath it.

Use `/pm:autoplan` when you want a full-rigor project planned without sitting through the interviews; use `/pm:express` instead when the work is small and you'd rather shape a compressed plan by hand. What autoplan does NOT do: it never claims, executes, verifies, completes, or releases, and never commits or pushes.

#### `/pm:complete [slug] [task-id] [--checkout-main]`
Marks a verified task as complete and opens the PR. Commits any remaining implementation changes, pushes the branch, opens a PR via `gh pr create` with the task file as the PR description, and records the PR URL on the task. Refuses if status isn't `done`.

```
/pm:complete usage-billing                      # auto-picks next done-but-not-PR'd task
/pm:complete usage-billing 003                  # complete a specific task
/pm:complete usage-billing 003 --checkout-main  # also pull main and switch to it
```

By default stays on the task branch so you can address PR feedback. `--checkout-main` is the one-step "I'm done, on to the next task" mode. If a PR already exists for the branch (e.g. you ran `/pm:complete` once, then `/pm:execute` again to address verify rejection), `/pm:complete` just pushes the latest commits — the existing PR updates automatically.

#### `/pm:resume <slug> [task-id]`
Switches back to a task's branch and pulls latest. Use when you've moved to a different branch (e.g. after `/pm:complete --checkout-main`) and need to come back — typically for PR comments or a post-merge `/pm:verify` rejection.

```
/pm:resume usage-billing                        # lists your tasks, asks which to resume
/pm:resume usage-billing 003                    # straight to task 003's branch
```

Refuses on a dirty working tree (would lose uncommitted work). Prints the task state and a status-aware next-step hint when you arrive — if the task was rejected, it shows the most recent Verifier notes so you know what to fix.

---

### Versioning

#### `/pm:version <slug> <new-version>`
Scaffolds the next milestone folder after v1 ships. Runs a mini PRD-style interview scoped to "what's in this version" — seeded from the prior version's `RELEASE.md` known-limitations section and any PRD goals not yet delivered.

```
/pm:version recurring-s3-exports v2
```

Creates `v2/goals.md`, empty `v2/research/` and `v2/tasks/`, and updates the PRD's `active_version` frontmatter. The previous version's folder stays frozen.

#### `/pm:release <slug> [version]`
Closes out a version. Refuses to release if any task isn't `done`. Asks for the release tag, deviations from goals, evidence links (PRs/SHAs), and known limitations carrying forward. Writes a frozen `RELEASE.md` and optionally maintains a `CHANGELOG.md` at the project root.

```
/pm:release recurring-s3-exports         # releases active version
/pm:release recurring-s3-exports v1      # releases a specific version
```

---

### Jira integration (optional)

Pm can optionally mirror task state to a Jira board. Enable per-project via `/pm:jira-init`; once enabled, the core lifecycle commands (`/pm:claim`, `/pm:verify`, `/pm:complete`, `/pm:version`, `/pm:release`) push status transitions and comments to Jira automatically on a **best-effort** basis — pm task state is always the source of truth, and Jira errors never block the pm flow.

#### `/pm:jira-init [slug]`
Interactive setup. Verifies `acli` (Atlassian's official CLI) is installed and authenticated, then writes `.pm/<slug>/.jira.yml` capturing site, project key, default issue types, and status-name mapping. Status names are seeded from your Jira project's actual workflow but fully editable so any custom workflow works. Offers to create the active version's epic and backfill Jira issues for existing tasks.

```
/pm:jira-init usage-billing
```

Requires `acli` — install from <https://developer.atlassian.com/cloud/acli/> and run `acli auth login` first.

#### `/pm:jira-link <slug> [task-id] <ISSUE-KEY>`
Attach an existing Jira issue (e.g. created in a planning meeting) to a pm task. Validates the key, refuses to overwrite an existing link without confirmation, and pushes the current pm status to Jira after linking.

```
/pm:jira-link usage-billing 003 PROJ-127
```

#### `/pm:jira-create <slug> [task-id]`
Create new Jira issue(s) from pm task(s). With a task id, creates one. Without, offers to batch-create issues for every unlinked task in the active version. The Jira issue's summary = task title, description = task body, parent = the active version's epic (if set), labels include the project slug and version.

```
/pm:jira-create usage-billing            # batch — creates issues for all unlinked tasks
/pm:jira-create usage-billing 005        # just task 005
```

#### `/pm:jira-sync [slug]`
Reconcile Jira with pm. For every linked task, push the current pm status to Jira. Useful after a sync failure, on first-run when enabling Jira on an existing project, or when Jira state has drifted (manual edits, bot interference). Read-only on pm — Jira is the side that moves.

```
/pm:jira-sync usage-billing
```

#### What gets synced when

| pm action            | Jira action                                                              |
|----------------------|--------------------------------------------------------------------------|
| `/pm:claim`          | Transition issue → `status_mapping.claim` (e.g. "In Progress"); set assignee by email lookup if enabled |
| `/pm:verify` accept  | Transition issue → `status_mapping.verify_accept` (e.g. "In Review")     |
| `/pm:verify` reject  | Transition issue → `status_mapping.verify_reject`; add comment with Verifier notes |
| `/pm:complete`       | Transition issue → `status_mapping.complete`; comment with PR URL        |
| `/pm:version vN`     | Create Jira epic for vN; record `jira_epic` in `vN/goals.md`             |
| `/pm:release`        | Transition the version's epic → `status_mapping.release_epic` (e.g. "Done") with release-tag comment |

#### `.jira.yml` example

```yaml
site: company.atlassian.net
project_key: PROJ
default_issue_type: Story
epic_issue_type: Epic
status_mapping:
  claim: "In Progress"
  verify_accept: "In Review"
  verify_reject: "In Progress"
  complete: "In Review"
  release_epic: "Done"
post_pr_comment_on_complete: true
sync_assignee_on_claim: true
```

The file is committable (no credentials live in it — `acli auth login` handles those). Adapt the status names to match your team's workflow; everything downstream reads from this file.

#### Failure handling

- If `.pm/<slug>/.jira.yml` doesn't exist, nothing happens. Jira is fully opt-in per project.
- If `acli` is missing or not authenticated when a sync would happen, a single one-line warning prints (`Jira sync skipped — acli not available. Run /pm:jira-init for setup.`) and the pm command continues.
- If an `acli` call fails for any other reason, a one-line warning prints naming the affected task and the error, and pm continues. Use `/pm:jira-sync` later to retry.
- Pm state is never rolled back on Jira failure.

---

### Read-only utilities

#### `/pm:status [slug]`
Dashboard: project title, status, active version, amendment count, per-version task counts, current blockers, and the recommended next command.

```
/pm:status recurring-s3-exports
```

#### `/pm:list`
Every project under `.pm/`, one line each. Sorted active-first.

```
/pm:list
```

#### `/pm:next [slug]`
Peek at the next ready task without executing. Shows the task's acceptance criteria, deps, and (if rejected) the verifier notes that need addressing.

```
/pm:next recurring-s3-exports
```

#### `/pm:gantt [slug] [version]`
Render a mermaid `gantt` chart of a version's tasks, using each task's `complexity` score as a relative duration and `depends_on` for ordering. Paste the emitted block into GitHub, a PR, or any markdown preview. Defaults to the active version.

```
/pm:gantt recurring-s3-exports
/pm:gantt recurring-s3-exports v2
```

---

## A complete worked example

Say you want to add a billing system to your app.

**1. Capture the idea.**
```
/pm:prd "add usage-based billing with Stripe for our SaaS"
```
The PM and a fintech-billing SME ask about pricing model (per-seat vs metered vs tiered), grandfathering, invoice format, dunning, tax handling, and so on. PRD lands at `.pm/usage-billing/prd.md`.

**2. Research.**
```
/pm:research usage-billing
```
The orchestrator picks `security-architect`, `data-modeler`, `integration-engineer` (Stripe API), `compliance-and-legal` (tax/PCI), `existing-codebase-archaeologist`, and `test-strategist`. Six parallel subagents write six reports. The `_index.md` surfaces three open questions about tax jurisdictions; you answer them, and one answer triggers `/pm:amend` to update the PRD.

**2.5. Architect.**
```
/pm:architect usage-billing
```
Principal Architect + Java/Spring SME (the repo is brownfield Spring Boot) walk you through deployment topology, scaling, sync vs async (Stripe webhooks → SQS for retries), multi-tenancy (row-level by org_id), data layer (Postgres + Redis cache), and the full tech stack. You accept most recommendations and override `Cache` to use the existing Hazelcast cluster instead of Redis. `architecture.md` lands at `.pm/usage-billing/v1/architecture.md`.

**2.6. (Optional) Test strategy.**
```
/pm:test usage-billing
```
QA Lead + Java/Spring Test SME walk you through levels (unit-heavy, integration via Testcontainers for Stripe webhooks, no e2e this version), the must-cover map (webhook idempotency, proration math, dunning state machine — each tied to PRD sections), fixtures (factory methods over static JSON), and CI gating (`mvn verify` gates merges). `testing.md` lands at `.pm/usage-billing/v1/testing.md` and now binds execution and verification.

**3. Plan.**
```
/pm:plan usage-billing
```
You get 14 ordered tasks. Task 001 sets up Stripe webhooks scaffolding, 002 adds the customer/subscription tables, 003 wires up checkout flow, etc. Dependencies are explicit (004 depends on 002, 003).

**3a. (Optional) Wire up Jira.**
```
/pm:jira-init usage-billing              # interactive — sets up .pm/usage-billing/.jira.yml + v1 epic
/pm:jira-create usage-billing            # batch-creates a Jira issue for each task
```
From here on, every claim/verify/complete also pushes status to your Jira board. Skip this step entirely if you don't use Jira.

**4. Execute, verify, complete, repeat.**
```
/pm:claim usage-billing                  # claims 001, switches to pm/usage-billing/001-stripe-webhooks
/pm:execute usage-billing                # implementation happens, java-guidelines skill triggers automatically
/pm:verify usage-billing                 # accepts 001
/pm:complete usage-billing --checkout-main  # opens PR, back on main, ready for next

/pm:claim usage-billing                  # claims 002
/pm:execute usage-billing
/pm:verify usage-billing                 # rejects 002 — "schema missing idempotency on webhook event ids"
/pm:execute usage-billing 002            # re-attempts with verifier notes in hand
/pm:verify usage-billing                 # accepts
/pm:complete usage-billing               # opens PR, stay on branch in case of feedback
```

A reviewer leaves a comment on the 001 PR. You're on the 002 branch:
```
/pm:resume usage-billing 001             # back on 001's branch, pulled latest
# ... fix the issue, commit ...
git push                                 # PR updates
/pm:resume usage-billing 002             # back to where you were
```

**5. Ship v1.**
```
/pm:release usage-billing
```
You provide release tag `v1.0.0-billing`, list deviations (metered billing deferred), paste PR links. `v1/RELEASE.md` is written and frozen.

**6. Start v2.**
```
/pm:version usage-billing v2
```
Mini-interview captures v2 scope (metered billing, annual contracts). The active version flips. `architecture.md` is copied from v1 to v2 with an inheritance amendment recorded. You're ready to `/pm:research usage-billing` and `/pm:architect usage-billing` (amend mode) for the v2-specific concerns.

---

## Tips and gotchas

- **Slug stability matters.** Once `.pm/<slug>/` exists, don't rename it casually — task `depends_on` references and amendment history are scoped to the project, not the slug.
- **Acceptance criteria must be observable.** "Code is clean" is not a criterion the verifier can check; "all `mvn verify` checks pass and `BillingServiceTest` has >80% coverage of the new methods" is.
- **A task is too big** if its acceptance criteria can't be reviewed in one focused pass. Ask `/pm:plan` to split it (or edit the table before files are written).
- **A task is too small** if it's a one-line change with no testable surface. Fold it into a sibling.
- **Don't skip `/pm:verify`.** The verifier runs in an independent context — that's the whole point. Letting the executor self-certify defeats the design.
- **Use `/pm:amend` not edits.** If you discover the PRD was wrong, amending preserves the audit trail. Direct edits to `prd.md` work too but lose the "why" of the change.
- **Architecture decisions are per-version and inherit by default.** `/pm:version vN` copies the prior version's `architecture.md` (and `testing.md`, if present) and records an inheritance Amendment. Re-run `/pm:architect <slug>` (or `/pm:test <slug>`) in amend mode to capture vN-specific changes, rather than rewriting from scratch.
- **The architecture file is binding.** `/pm:execute` reads it before coding and refuses to silently substitute; `/pm:verify` rejects drift. If you genuinely need a different decision mid-execution, `/pm:architect <slug>` in amend mode first, then continue.
- **The test strategy is optional but binding when present.** No `testing.md`, no friction — tests follow repo conventions. With one, `/pm:verify` rejects test drift unless the Implementation summary justifies the deviation. `/pm:version` inherits it like `architecture.md`.
- **Versions are for shipped milestones, not branches.** If you're exploring a risky direction, a git branch is the right tool. A new `vN` folder is appropriate when you've shipped vN-1 and are planning the next deliverable cut.
- **Brownfield projects** auto-include the `existing-codebase-archaeologist` persona during research, which surfaces the patterns and integration points the new work must respect.
- **Jira sync is best-effort** — pm task state is the source of truth on disk. If a transition silently fails (acli down, permission gap, workflow change), use `/pm:jira-sync` to reconcile. Never reach for git revert because Jira didn't update.

---

## Model selection

Each command ships with a model pre-selected for its workload, so you're not paying premium for tasks a cheaper model handles fine. The defaults strike a balance between quality where it matters (planning, verification) and cost on everything else.

### Defaults

| Tier | Commands | Why |
|---|---|---|
| **Opus** (judgment / synthesis) | `/pm:prd`, `/pm:express`, `/pm:amend`, `/pm:research`, `/pm:rerun-research`, `/pm:architect`, `/pm:test`, `/pm:plan`, `/pm:replan`, `/pm:verify`, `/pm:handoff`, `/pm:version` | Multi-source synthesis, two-persona interviews, architecture and task decomposition with dependencies, independent acceptance-criteria judgment, distilling session context into a useful handoff. Express runs PRD interview, persona selection, and task decomposition in one pass — compression is high-judgment work. |
| **Sonnet** (code / git / mechanical) | `/pm:execute`, `/pm:auto`, `/pm:autoplan`, `/pm:complete`, `/pm:claim`, `/pm:resume`, `/pm:release`, `/pm:jira-init`, `/pm:jira-link`, `/pm:jira-create`, `/pm:jira-sync` | Code generation, git workflow, frontmatter edits, acli/gh shell-outs. Sonnet 4.6 handles these at a fraction of Opus cost. |
| **Haiku** (read-only display) | `/pm:status`, `/pm:list`, `/pm:next`, `/pm:gantt` | Read frontmatter, format output, conditional sections. No judgment required. |

**`/pm:research` also dispatches its persona subagents on Sonnet** (the orchestrator stays on Opus). Each persona writes a focused ~800-word report — well within Sonnet's strength — and dispatching 3–6 in parallel makes the cost difference matter.

**`/pm:auto` preserves the tiering across its loop:** the orchestrator stays on Sonnet (task picking, status checks — mechanical), while each execute subagent runs on Sonnet and each verify subagent on Opus, matching what `/pm:execute` and `/pm:verify` would use standalone.

**`/pm:autoplan` preserves the tiering across its pipeline:** the orchestrator stays on Sonnet (sequencing stages, presence checks — mechanical), while each authoring stage subagent runs on Opus (matching what `/pm:prd`, `/pm:research`, `/pm:architect`, `/pm:test`, and `/pm:plan` use standalone), and the read-only artifact presence checks run on Haiku.

### Overriding the model for a command

Use Claude Code's native command-override mechanism: drop a thin override file in your project's `.claude/commands/pm/<command>.md` (or your user-level commands directory) with just the model frontmatter:

```yaml
---
model: opus
---
```

Project-level files take precedence over plugin commands, so this is enough. You don't need to copy the command body — Claude Code merges the override on top of the plugin's defaults. Common overrides:

- **Always use Opus for `/pm:execute`** when your project's code is particularly tricky and you want the extra rigor.
- **Always use Sonnet for `/pm:plan`** if you trust the model and want planning to be cheaper / faster.
- **Always use Haiku for `/pm:jira-sync`** if you have lots of issues and want the cheapest reconciliation possible.

---

## Multi-developer usage

The plugin works on teams, but the workflow needs to be deliberate. Headline pattern: **one lead plans, many engineers execute in parallel, branch per task, git is the concurrency control.**

### Recommended workflow

**1. One lead initiates the planning.**
`/pm:prd`, `/pm:research`, `/pm:plan` are sequential and synthesize input — running them in parallel produces conflicting PRDs and task lists. One person runs them (often after a kickoff meeting), opens a PR with the `.pm/<slug>/` folder, the team reviews and merges. After that, the planning artifacts are shared source of truth.

**`/pm:express` is a solo / small-team tool.** It's appropriate when one engineer is scoping a focused piece of work themselves — a small feature, a fix, a prototype — and doesn't need a kickoff meeting to decide what to build. For larger work the full pipeline's PR-driven planning review is still the right pattern; express skips that review by design.

**2. Branch per task.**
Convention: `pm/<slug>/<task-id>-<short-slug>` (e.g. `pm/usage-billing/003-stripe-webhooks`). The task file IS the PR description — it has the goals, acceptance criteria, research links, and (after `/pm:execute`) the implementation summary. Reviewers get full context for free.

**3. Claim before you execute.**
Run `/pm:claim <slug>` (or `/pm:claim <slug> <id>` for a specific task). It pulls latest, creates the `pm/<slug>/<id>-<slug>` branch, flips status to `in-progress`, sets `assignee` from your git config, commits, and pushes — all in one step. Teammates running `/pm:next` or `/pm:status` immediately see the task is taken. If two people race, the second push is rejected by git and that engineer picks another task. Optimistic locking via git, no central server.

**3a. Handing a task to a teammate mid-flight.**
If you need to stop mid-task and pass the work to someone else (going on leave, end of sprint, hit a domain wall), the clean two-step is `/pm:handoff <slug> <id>` (captures your in-flight context onto the task body and pushes) followed by your teammate running `/pm:claim <slug> <id> --force` from their machine (takes over the claim and assignee). They then `/pm:execute` and pick up the handoff notes as part of normal task body reading — no flag, no out-of-band coordination. The same `/pm:handoff` step is also useful solo: when context runs out at end of day, leave a handoff for tomorrow-you.

**4. Verification has two layers.**
- `/pm:verify` (Claude-as-verifier) — run by the executor or a teammate. Independent context, checks against PRD + acceptance criteria. Writes verifier notes into the task file.
- **PR review** (human) — on top of Claude's verdict. The reviewer sees the task, Claude verifier notes, diff, and test results in one PR and focuses on judgment calls Claude can't make: architectural fit, team conventions, business risk.

For maximum rigor, the `/pm:verify` operator is a different human than the executor. For speed, same person is fine — the PR reviewer is your independent check.

**5. PRD changes go through PR review.**
`/pm:amend` is append-only (good for merging), but amendments still affect everyone's pending work. Treat `.pm/<slug>/prd.md` and `goals.md` like code: require review. Consider a CODEOWNERS rule on `.pm/`.

**6. `/pm:version` is a lead activity.**
Same as initial planning — one person scaffolds vN with team input.

### Role split at a glance

| Activity              | Who runs it                              |
|-----------------------|------------------------------------------|
| `/pm:prd`             | Lead, once                               |
| `/pm:research`        | Lead, with team input on persona picks   |
| `/pm:architect`       | Lead, with team review of tech-stack picks |
| `/pm:test`            | Lead, with team review of the strategy   |
| `/pm:plan`            | Lead, with team review of the task table |
| `/pm:claim`           | Any engineer, before executing           |
| `/pm:execute`         | Any engineer, after `/pm:claim`          |
| `/pm:handoff`         | Any engineer, when stopping mid-task     |
| `/pm:verify`          | Executor (fast) or teammate (rigorous)   |
| `/pm:auto`            | Any engineer — respects others' claims automatically |
| `/pm:complete`        | Any engineer, after `/pm:verify` accepts |
| `/pm:resume`          | Any engineer, to return to a task        |
| `/pm:amend`           | Lead, via PR                             |
| `/pm:replan`          | Lead, after amendment is merged          |
| `/pm:release`         | Lead, once per version                   |
| `/pm:version`         | Lead, once                               |
| `/pm:status`, `/pm:list`, `/pm:next`, `/pm:gantt` | Anyone, anytime      |

### Known gaps to be aware of

- **Concurrent claims race.** If two devs both pull at the same SHA and both run `/pm:claim` simultaneously, the second push is rejected — they pull, see the task is taken, and pick another. Mildly annoying, not destructive.
- **Task file merge conflicts** if executor and verifier edit simultaneously. Mitigation: don't run `/pm:execute` and `/pm:verify` from separate worktrees on the same task at the same time. The PR pattern naturally serializes this — verify runs against the PR branch, not main.
- **Research `_index.md` is a single file.** Concurrent `/pm:research` runs would conflict. Not an issue in practice because research is a lead activity that happens once per version.

### TL;DR

> Lead does `/pm:prd` → `/pm:research` → `/pm:plan`, opens a PR with the planning artifacts. Engineers run `/pm:claim` to grab a task (creates branch + flips status + pushes), then `/pm:execute`, `/pm:verify`, and `/pm:complete` to open the PR. Human reviews on top of Claude's verify verdict, merges. `/pm:resume` brings you back to a branch when PR feedback needs addressing. Lead handles `/pm:amend`, `/pm:release`, `/pm:version`.

---

## Persona catalog

The full research persona catalog ships at `plugins/pm/personas.md`. Add or modify personas there if you want a custom set — the orchestrator reads the catalog at each `/pm:research` run.

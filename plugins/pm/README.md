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

All commands are prefixed `pm-` to avoid collisions with other plugins.

---

## Mental model

Every project lives under `.pm/<project-slug>/` in your repo. The folder is committable, portable, and human-readable.

```
.pm/<slug>/
├── prd.md              # canonical product vision; append-only Amendments section
├── README.md           # auto-generated folder explainer
├── v1/
│   ├── goals.md        # what v1 delivers (cut from PRD)
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
    ├── research/
    └── tasks/
```

Each task file is markdown with YAML frontmatter capturing `status`, `depends_on`, `prd_refs`, and `acceptance_criteria`. Status flows: `pending → in-progress → done-pending-verify → done` (or `→ rejected → pending` on a verify rejection).

### The flow

```
/pm-prd       →   /pm-research    →   /pm-plan    →   /pm-execute    →   /pm-verify
   ▲                                                         │
   │                                                         ▼ (rejected loops back)
   /pm-amend  ──→  /pm-replan                          /pm-release  →  /pm-version v2
```

You can skip stages (`/pm-plan` will warn if there's no research but proceed) — the structure is opinionated, not rigid.

---

## Commands

### Project lifecycle

#### `/pm-prd <one-line idea>`
Two personas — a Senior PM and a dynamically-picked domain SME — interview you to fill gaps, then draft `prd.md` and scaffold `v1/`.

```
/pm-prd "build a tool that lets users schedule recurring exports to S3"
```

You'll get tagged questions like `[PM] Who are the primary users — engineers running ad-hoc exports, or ops teams setting up scheduled pipelines?` and `[SME-data-platform] What data sources are in scope — S3, RDS, warehouses, or all of the above?` After 2–4 rounds, the PRD is drafted and shown to you for edits before writing.

#### `/pm-amend <slug>`
Append a dated, append-only amendment to the PRD. Use after research surfaces something that changes scope, or when stakeholders shift requirements mid-flight.

```
/pm-amend recurring-s3-exports
```

The PRD's original body stays intact; the amendment is recorded under `## Amendments` with a `Why:`, `Change:`, and `Impact on pending work:` line. If you say "yes, this affects pending tasks", you'll be pointed at `/pm-replan` next.

---

### Research

#### `/pm-research [slug]`
Reads the PRD and active version's `goals.md`, picks 3–6 personas from the catalog (`plugins/pm/personas.md`) — security architect, data modeler, UX researcher, SRE, integration engineer, performance engineer, accessibility specialist, compliance/legal, test strategist, migration strategist, and the existing-codebase archaeologist for brownfield repos — then dispatches them as **parallel Agent subagents**. Each writes its own report referencing PRD/goals sections.

```
/pm-research recurring-s3-exports
```

You confirm the persona picks (with the option to add/remove) before dispatch. After all subagents return, an `_index.md` rolls up cross-cutting open questions. If those questions materially change scope, you'll be prompted to `/pm-amend`.

#### `/pm-rerun-research <slug> <persona-slug>`
Re-runs a single persona — useful when a PRD amendment invalidates one report, or when a persona's first pass was thin. The prior report is archived to `research/.archive/` so nothing is lost.

```
/pm-rerun-research recurring-s3-exports security-architect
```

---

### Planning

#### `/pm-plan [slug]`
Turns PRD + research into ordered task files. Each task is atomic, executable in one `/pm-execute` session, and includes acceptance criteria the verifier can check. Dependencies are declared explicitly so `/pm-execute` can auto-pick the next ready task.

```
/pm-plan recurring-s3-exports
```

You see the full task list as a table before any files are written, and you can edit (add/remove/reorder/rename) before committing. Each task file gets a 3-digit zero-padded id (`001`, `002`, …) so they sort naturally.

#### `/pm-replan [slug]`
Regenerates pending/rejected tasks from the (possibly amended) PRD while **preserving** anything that's `done`, `done-pending-verify`, or `in-progress`. Replaced tasks are archived to `tasks/.archive/` rather than deleted.

```
/pm-replan recurring-s3-exports
```

Shown as a diff: `Preserving 3 / Replacing 2 / Adding 4` so you can confirm before files change.

---

### Execution and verification

#### `/pm-execute [slug] [task-id]`
The specialist coding agent. Runs in your main thread so you can intervene mid-task. Detects your stack (pom.xml, package.json, pyproject.toml, etc.) and triggers any relevant skills (e.g. `java-guidelines`, `frontend-design`) and reads any `CLAUDE.md` files. Reads the task, the PRD sections it references, and the relevant research files before writing a single line of code.

```
/pm-execute recurring-s3-exports         # auto-picks lowest-id ready task
/pm-execute recurring-s3-exports 003     # forces task 003 (warns if deps unmet)
```

Status transitions: flips to `in-progress` when work starts, `done-pending-verify` when complete. Appends an `## Implementation summary` to the task body listing files changed, criterion-by-criterion satisfaction with `file:line` evidence, and notes for the verifier.

If a previously rejected task is picked up, the executor reads the existing `## Verifier notes` and addresses each gap, then writes a `## Re-execution notes` section explaining how.

#### `/pm-verify [slug] [task-id]`
A Senior QA / Tech Lead persona that **independently** verifies the work. Reads the PRD, research, task, and the actual diff (`git status` / `git diff`). Runs tests if the implementation summary specifies a command. Judges each acceptance criterion as PASS / FAIL / PARTIAL / UNVERIFIABLE with evidence.

```
/pm-verify recurring-s3-exports          # auto-picks lowest-id done-pending-verify task
/pm-verify recurring-s3-exports 003      # verify a specific task
```

On accept: status `done`, brief accepted note appended.
On reject: status `rejected`, plus a `## Verifier notes` section listing **specific, actionable gaps** so the next `/pm-execute` (which may be a different session entirely) can pick up cold and finish the work correctly.

---

### Versioning

#### `/pm-version <slug> <new-version>`
Scaffolds the next milestone folder after v1 ships. Runs a mini PRD-style interview scoped to "what's in this version" — seeded from the prior version's `RELEASE.md` known-limitations section and any PRD goals not yet delivered.

```
/pm-version recurring-s3-exports v2
```

Creates `v2/goals.md`, empty `v2/research/` and `v2/tasks/`, and updates the PRD's `active_version` frontmatter. The previous version's folder stays frozen.

#### `/pm-release <slug> [version]`
Closes out a version. Refuses to release if any task isn't `done`. Asks for the release tag, deviations from goals, evidence links (PRs/SHAs), and known limitations carrying forward. Writes a frozen `RELEASE.md` and optionally maintains a `CHANGELOG.md` at the project root.

```
/pm-release recurring-s3-exports         # releases active version
/pm-release recurring-s3-exports v1      # releases a specific version
```

---

### Read-only utilities

#### `/pm-status [slug]`
Dashboard: project title, status, active version, amendment count, per-version task counts, current blockers, and the recommended next command.

```
/pm-status recurring-s3-exports
```

#### `/pm-list`
Every project under `.pm/`, one line each. Sorted active-first.

```
/pm-list
```

#### `/pm-next [slug]`
Peek at the next ready task without executing. Shows the task's acceptance criteria, deps, and (if rejected) the verifier notes that need addressing.

```
/pm-next recurring-s3-exports
```

---

## A complete worked example

Say you want to add a billing system to your app.

**1. Capture the idea.**
```
/pm-prd "add usage-based billing with Stripe for our SaaS"
```
The PM and a fintech-billing SME ask about pricing model (per-seat vs metered vs tiered), grandfathering, invoice format, dunning, tax handling, and so on. PRD lands at `.pm/usage-billing/prd.md`.

**2. Research.**
```
/pm-research usage-billing
```
The orchestrator picks `security-architect`, `data-modeler`, `integration-engineer` (Stripe API), `compliance-and-legal` (tax/PCI), `existing-codebase-archaeologist`, and `test-strategist`. Six parallel subagents write six reports. The `_index.md` surfaces three open questions about tax jurisdictions; you answer them, and one answer triggers `/pm-amend` to update the PRD.

**3. Plan.**
```
/pm-plan usage-billing
```
You get 14 ordered tasks. Task 001 sets up Stripe webhooks scaffolding, 002 adds the customer/subscription tables, 003 wires up checkout flow, etc. Dependencies are explicit (004 depends on 002, 003).

**4. Execute, verify, repeat.**
```
/pm-execute usage-billing                # picks 001
# ... implementation happens, java-guidelines skill triggers automatically ...
/pm-verify usage-billing                 # accepts 001
/pm-execute usage-billing                # picks 002
/pm-verify usage-billing                 # rejects 002 — "schema missing idempotency on webhook event ids"
/pm-execute usage-billing 002            # re-attempts with verifier notes in hand
/pm-verify usage-billing                 # accepts
```

**5. Ship v1.**
```
/pm-release usage-billing
```
You provide release tag `v1.0.0-billing`, list deviations (metered billing deferred), paste PR links. `v1/RELEASE.md` is written and frozen.

**6. Start v2.**
```
/pm-version usage-billing v2
```
Mini-interview captures v2 scope (metered billing, annual contracts). The active version flips. You're ready to `/pm-research usage-billing` again for the v2-specific concerns.

---

## Tips and gotchas

- **Slug stability matters.** Once `.pm/<slug>/` exists, don't rename it casually — task `depends_on` references and amendment history are scoped to the project, not the slug.
- **Acceptance criteria must be observable.** "Code is clean" is not a criterion the verifier can check; "all `mvn verify` checks pass and `BillingServiceTest` has >80% coverage of the new methods" is.
- **A task is too big** if its acceptance criteria can't be reviewed in one focused pass. Ask `/pm-plan` to split it (or edit the table before files are written).
- **A task is too small** if it's a one-line change with no testable surface. Fold it into a sibling.
- **Don't skip `/pm-verify`.** The verifier runs in an independent context — that's the whole point. Letting the executor self-certify defeats the design.
- **Use `/pm-amend` not edits.** If you discover the PRD was wrong, amending preserves the audit trail. Direct edits to `prd.md` work too but lose the "why" of the change.
- **Versions are for shipped milestones, not branches.** If you're exploring a risky direction, a git branch is the right tool. A new `vN` folder is appropriate when you've shipped vN-1 and are planning the next deliverable cut.
- **Brownfield projects** auto-include the `existing-codebase-archaeologist` persona during research, which surfaces the patterns and integration points the new work must respect.

---

## Persona catalog

The full research persona catalog ships at `plugins/pm/personas.md`. Add or modify personas there if you want a custom set — the orchestrator reads the catalog at each `/pm-research` run.

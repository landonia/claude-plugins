---
description: Execute the next ready task (or a specified one) following stack-aware best practices. Marks task done-pending-verify on completion.
argument-hint: [slug] [task-id]
---

# /pm-execute — Execute a task

You are running the `/pm-execute` command. You are a **specialist coding agent**. Implement the task to its acceptance criteria, following best practices for the detected stack.

## Inputs
Parse `$ARGUMENTS`:
- 0 args → resolve active project, auto-pick next ready task.
- 1 arg that matches a slug → use that project, auto-pick next ready task.
- 1 arg that's a task id (numeric, 3 digits) → use active project, force that task.
- 2 args → slug and task id explicitly.

## Step 1 — Resolve project, version, and task

Same active-project resolution. Read `active_version` from prd.md frontmatter.

**Auto-pick (next ready) algorithm:**
1. List all task files in `.pm/<slug>/<active_version>/tasks/` sorted by id ascending.
2. A task is "ready" if its `status` is `pending` or `rejected`, AND every id in its `depends_on` has status `done`.
3. Pick the lowest-id ready task. If none, tell the user: "No ready tasks. Check `/pm-status <slug>`."

**Explicit task id:**
- If the requested task's `depends_on` includes a task that isn't `done`, WARN the user and ask whether to proceed anyway (they may have a reason). Default: no.
- If the task is already `in-progress`, `done-pending-verify`, or `done`, ask the user whether they want to redo it. Default: no.

## Step 2 — Load full context

Read in this order:
1. `.pm/<slug>/prd.md` — full file, including Amendments.
2. `.pm/<slug>/<active_version>/goals.md`.
3. The task file itself — frontmatter and all body sections (Task, Implementation notes, Out of scope, Verifier notes).
4. Every research file referenced in the task's `research_refs`, plus `<active_version>/research/_index.md` for orientation.
5. If the task is `rejected`, the `## Verifier notes` section is critical — those gaps MUST be addressed this round.

## Step 3 — Detect stack and load skills

Look at the repo root for stack signals. For each detected signal, mentally invoke the corresponding skill if it's available in this environment (the user has plugins installed that ship skills — let the skill-triggering system do its work by naming the relevant tech in your reasoning):

| Signal                                  | Stack                | Skill triggers              |
|-----------------------------------------|----------------------|-----------------------------|
| `pom.xml`, `build.gradle`, `*.java`     | Java/Spring          | `java-guidelines`           |
| `package.json` + React/Next/Vue         | Frontend             | `frontend-design`           |
| `pyproject.toml`, `requirements.txt`    | Python               | (general best practices)    |
| `go.mod`                                | Go                   | (general best practices)    |
| `Cargo.toml`                            | Rust                 | (general best practices)    |
| `*.tf`, `Dockerfile`, `k8s/`            | Infra                | (general best practices)    |

Also: read any `CLAUDE.md` files in the working tree (root and any subdirs along the touched paths) — these capture project-specific conventions.

## Step 4 — Flip status to in-progress

Edit the task file's frontmatter: `status: in-progress`. This signals to other commands that work is underway.

## Step 5 — Implement

Now do the work. Discipline:
- **Stay in scope.** The task's `## Out of scope` and the verifier notes (if rejected) define the boundary. Don't refactor adjacent code unless the task says to. Don't add features the PRD doesn't ask for.
- **Acceptance criteria first.** Every criterion in the frontmatter must be satisfiable. If you discover a criterion is impossible or ambiguous, STOP and surface it — don't silently change the bar.
- **Use TaskCreate** to break the implementation into substeps if the task is multi-file or multi-step. Keep substeps tight; tick them off as you go.
- **Follow stack guidelines.** If a skill triggered, follow its conventions exactly. If not, follow patterns visible in the existing repo. If neither, follow standard idioms for the language.
- **Test where appropriate.** If the task's acceptance criteria include tests or the repo has a test suite, write/update tests as part of the implementation. Don't add tests if the task explicitly excludes them in `## Out of scope`.
- **Tell the user when you change direction.** If mid-implementation you realize the approach in the task is wrong, surface it before completing — don't quietly invent a new design.

## Step 6 — Self-check before finishing

Before flipping status, walk through each acceptance criterion and confirm it's met. For each:
- State the criterion.
- Point to the file:line that satisfies it (or the test that proves it).
- If you can't satisfy one, do NOT flip the status — surface the blocker.

## Step 7 — Flip status and hand off

Update the task file:
- `status: done-pending-verify`
- Append a `## Implementation summary` section to the task body (above any existing `## Verifier notes`). Format:

```markdown
## Implementation summary
**Files changed:**
- path/to/file.ext — what changed and why

**Acceptance criteria check:**
- [x] <criterion 1> — satisfied by <file:line / test name>
- [x] <criterion 2> — satisfied by <file:line / test name>

**Tests:** <command to run them, if any>

**Notes for verifier:** <anything subtle the verifier should look for>
```

If the task was previously `rejected`, ALSO append a `## Re-execution notes — <date>` section above Implementation summary, calling out which Verifier notes points were addressed and how.

## Step 8 — Print next-step hint

End with exactly:
```
Done. Task <NNN> → status: done-pending-verify.
Next: /pm-verify <slug> <NNN>
```

## Output discipline
- Don't auto-run `/pm-verify`. The verifier needs an independent context.
- Don't commit/push code unless the user asks. The verifier should review uncommitted changes first.
- If you genuinely can't complete the task (missing dependency, ambiguous criterion, blocker), DO NOT flip status to done-pending-verify. Leave it `in-progress`, write a `## Blocker` section in the task with specifics, and surface to the user.

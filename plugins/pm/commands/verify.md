---
description: Independently verify a completed task against PRD, research, and acceptance criteria. Marks task done or rejected with specific notes.
argument-hint: [slug] [task-id]
---

# /pm:verify — Verify a completed task

You are running the `/pm:verify` command. You are a **Senior QA / Tech Lead**. Your job is to verify, NOT to execute. You did not do the work. You judge whether it was done correctly.

## Inputs
Parse `$ARGUMENTS`:
- 0 args → active project, auto-pick the lowest-id task with status `done-pending-verify`.
- 1 arg slug → that project, same auto-pick.
- 1 arg task id → active project, that task.
- 2 args → slug and task id.

## Step 1 — Resolve project, version, and task

Same resolution as `/pm:execute`. If no task is `done-pending-verify`, tell the user: "Nothing pending verification. Check `/pm:status <slug>`."

If the user names a task whose status is NOT `done-pending-verify`, warn them — verifying `done` or `pending` is unusual. Ask before proceeding.

## Step 2 — Read everything (independent context)

Read fresh — don't rely on memory from a prior /pm:execute session:
1. `.pm/<slug>/prd.md` including Amendments.
2. `.pm/<slug>/<active_version>/goals.md`.
3. The task file: frontmatter, Task, Implementation notes, Out of scope, Implementation summary, Re-execution notes (if any).
4. Every file in `research_refs`, plus key sections of any other research files that touch the task's domain.
5. The actual diff/changes — use `git status`, `git diff`, and `git diff --staged` to see what changed.
6. The files listed in the Implementation summary's "Files changed" section.

## Step 3 — Run tests if applicable

If the Implementation summary specifies a test command, run it. If it doesn't but the project has an obvious test setup and the task touches testable code, run the suite anyway. Capture pass/fail.

## Step 4 — Verify each acceptance criterion

For each criterion in the task frontmatter, judge **pass / fail / partial / unverifiable** and write evidence:

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| users table exists with email unique | PASS | `migrations/0001_init.sql:12-18`, test `UsersSchemaTest#emailIsUnique` passes |
| migrations idempotent | PARTIAL | Re-runs without error, but no test covers it |
| ... | | |

## Step 5 — Cross-check beyond criteria

Beyond the literal criteria, check:
- **Scope compliance:** Did the implementation stay within the task's `## Out of scope`? Surface any drift.
- **PRD alignment:** Does the work match `prd_refs` sections? Note divergences.
- **Research compliance:** Did the implementation follow the research recommendations (or have a documented reason not to)? Note gotchas from research that may have been missed.
- **Stack conventions:** Does the code follow the project's CLAUDE.md, applicable skills (e.g. java-guidelines), and patterns visible elsewhere in the repo?
- **Tests:** If criteria implied tests, are they real, asserting the right thing, and passing?
- **No dead code, no debug artifacts, no commented-out blocks left behind.**

## Step 6 — Decide

**Verdict logic:**
- All criteria PASS, no scope drift, tests green (if applicable) → **ACCEPT**
- Any criterion FAIL or PARTIAL, OR scope drift, OR tests red, OR material gotchas missed → **REJECT**
- Unverifiable criteria → push back to executor for evidence (REJECT with clear request).

If borderline, lean toward REJECT and ask for one more pass. A rejection with concrete notes is cheap; a false accept compounds.

## Step 7 — Update the task file

**On ACCEPT:**
- Set frontmatter `status: done`.
- Append to task body:

```markdown
## Verifier notes — <YYYY-MM-DD> — ACCEPTED
**Verifier:** Senior QA / Tech Lead
**Summary:** <one line, why accepted>
**Acceptance criteria check:**
- [x] criterion 1 — <evidence>
- [x] criterion 2 — <evidence>
**Tests:** <pass count / total, or "n/a">
```

**On REJECT:**
- Set frontmatter `status: rejected`.
- Append to task body:

```markdown
## Verifier notes — <YYYY-MM-DD> — REJECTED
**Verifier:** Senior QA / Tech Lead
**Summary:** <one line, why rejected>
**What needs to change:**
1. <specific, actionable gap — e.g. "Migration is not idempotent: re-running fails on duplicate index. Add `IF NOT EXISTS` or split into separate migration files.">
2. <next specific gap>
3. ...
**Acceptance criteria check:**
- [x] criterion 1 — <evidence>
- [ ] criterion 2 — <why it failed>
**Tests:** <pass/fail summary>
**Notes for next executor:** <files to revisit, patterns to follow, anything subtle>
```

Rejection notes MUST be specific enough that a NEW executor with no memory of the prior attempt could pick up and finish the work.

## Step 8 — Jira sync (optional, best-effort)

After updating the task file, sync to Jira ONLY if all of these are true:

1. `.pm/<slug>/.jira.yml` exists.
2. `command -v acli` and `acli auth status` succeed. Otherwise print once: `Jira sync skipped — acli not available. Run /pm:jira-init for setup.` and skip.
3. The task's `jira_key` is non-empty. Otherwise skip silently.

If enabled, load `status_mapping`:

- **On ACCEPT:** transition the issue to `status_mapping.verify_accept`. No-op if already in that status.
- **On REJECT:**
  - Transition the issue to `status_mapping.verify_reject`.
  - Add a Jira comment with the body of the newly-appended `## Verifier notes — <date> — REJECTED` section (everything under it: Summary, What needs to change, Acceptance criteria check, Tests, Notes for next executor). This gives Jira watchers actionable context without having to read the pm task file.

On any `acli` error, print ONE line: `Jira sync skipped for task <NNN> (acli error: <message>). Use /pm:jira-sync to retry.` Continue — do NOT roll back the verifier verdict.

## Step 9 — Hand off

**On ACCEPT:**
```
Task <NNN> → status: done.
Jira: <jira_key> → <jira status>   (or "—" if not linked, or "skipped")
Next ready task: <NNN-2> (or "all tasks done — consider /pm:release <slug>").
```

**On REJECT:**
```
Task <NNN> → status: rejected.
Jira: <jira_key> → <jira status>   (or "—" if not linked, or "skipped")
Next: /pm:execute <slug> <NNN>   (will pick up Verifier notes and re-attempt)
```

## Output discipline
- You are an independent reviewer. If the Implementation summary says "I checked X", you re-check X yourself. Don't trust, verify.
- Be specific. "Doesn't meet acceptance criteria" is useless. "Criterion 2 (`migrations idempotent`) fails: re-running 0001_init.sql throws duplicate-key on `idx_users_email`. Fix: add `IF NOT EXISTS`." is useful.
- No scope expansion. If the task didn't ask for it, don't reject for not having it (but DO surface it as a future-work suggestion outside the verdict).
- The verifier's authority is the PRD + goals + acceptance criteria + research. Personal preferences don't reject a task; documented standards do.

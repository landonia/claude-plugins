---
description: Pause an in-progress task by writing a handoff note onto the task file so a different session — or a different developer — can pick up from where you stopped without re-deriving context.
model: opus
argument-hint: [slug] [task-id]
---

# /pm:handoff — Hand off an in-progress task

You are running the `/pm:handoff` command. The user is **stopping mid-task** and needs to leave behind enough context for the next executor to pick up.

The next executor will see the PRD, research, architecture, test strategy, and the task file — those are stable inputs already on disk. Your job here is to capture the **ephemeral, in-flight context that isn't anywhere else**: the approach taken so far, what's working, what's half-done, what the next concrete steps are, and any gotchas surfaced during implementation that no planning document anticipated.

A handoff is **context-passing, not ownership transfer.** The task stays `in-progress`, the assignee and branch are unchanged. A teammate who wants to take over runs `/pm:claim <slug> <NNN> --force` after picking up the handoff.

## Inputs

Parse `$ARGUMENTS`:
- 0 args → active project, auto-pick the user's current in-progress task.
- 1 arg slug → that project, auto-pick the user's current in-progress task.
- 1 arg task id (numeric, 3 digits) → active project, that task.
- 2 args → slug and task id.

## Step 1 — Resolve project, version, and task

Standard active-project resolution. Read `active_version` from prd.md frontmatter.

**Auto-pick:**
1. List task files in `.pm/<slug>/<active_version>/tasks/`.
2. Filter to tasks whose `status` is `in-progress` AND whose `assignee` matches the current `git config user.name` + `user.email`.
3. If exactly one match: use it.
4. If multiple: present them with AskUserQuestion — id, title, branch, `claimed_at`. User picks.
5. If none: tell the user "No in-progress tasks claimed by you. /pm:handoff only applies to active work — use /pm:status to see project state." and stop.

**Explicit task id:** verify the task exists and proceed to pre-flight.

## Step 2 — Pre-flight checks

1. **Inside a git repo.** Standard check.
2. **Git identity available.** `git config user.name` and `git config user.email` must both return non-empty values — they're recorded on the handoff's `From:` line. If either is empty, refuse with: "Set `git config user.name` and `git config user.email` first."
3. **Task status is `in-progress`.** Refuse otherwise:
   - `pending` → "Task <NNN> hasn't been claimed yet. /pm:handoff only applies to in-progress work."
   - `done-pending-verify` → "Task <NNN> is awaiting verification. Run /pm:verify <slug> <NNN>; if it accepts, run /pm:complete. If it rejects, the verifier notes already serve as the handoff for the next /pm:execute pass."
   - `done` → "Task <NNN> is complete."
   - `rejected` → "Task <NNN> is rejected; the verifier notes are the handoff. Run /pm:execute <slug> <NNN> to pick them up."
4. **On the task's branch.** Read the task's `branch:` field. If the current branch doesn't match, refuse with: "You're on `<current>`, not `<branch>`. Run /pm:resume <slug> <NNN> first, then /pm:handoff." (Handoffs always commit on the task's branch.)
5. **Remote exists.** `git remote get-url origin` must succeed. Refuse if no remote — the handoff needs to be visible to the next session, which means pushing.

Do NOT require a clean working tree. In-flight uncommitted changes are normal for a handoff — the whole point is to describe them. We'll commit the task file specifically (by path) without staging anything else.

## Step 3 — Synthesize a draft handoff

You have the session context fresh — the approach you took, files you touched, where you got stuck, gotchas you discovered. Pull that together into a draft following the template below. Then read the current state of the working tree to ground the **Current state** section: run `git status --porcelain`, `git diff --stat`, and `git diff --stat --staged` to enumerate touched files; reason about which are committed vs uncommitted.

**Draft template** (this is the exact shape that will be written to the task body):

```markdown
## Handoff notes — <YYYY-MM-DD>
**From:** <git user.name> <git user.email>
**Reason:** <one line — context budget exhausted, EOD, handing to teammate, blocked on X, etc.>
**Approach taken so far:** <high-level summary of the path attempted. Not a play-by-play.>
**Current state:**
- Files touched: <path — one bullet per file with what's in flight>
- Committed on branch: <what's done and stable>
- Uncommitted in working tree: <what's half-done; describe the in-progress diff at a level the next person can act on>
**Next steps:** <concrete, ordered list of what the next executor should do — first thing first>
**Gotchas / things not in PRD/research/architecture/test strategy:** <subtleties surfaced during implementation that the planning docs don't cover>
**Open questions:** <decisions that need to be made before continuing — leave empty if none>
```

**Authoring discipline — critical:**
- **Don't repeat planning content.** The task already references `prd_refs`, `arch_refs`, `test_refs`, `research_refs`. Don't restate the goal, the acceptance criteria, or the architectural decisions — the next executor will read those directly. Capture only what's *not* in any of those documents.
- **Be specific.** "Refactored the service layer" is useless. "Pulled out `BillingCalculator` to its own class at `src/billing/BillingCalculator.java`, but the `applyDiscounts` method still depends on the old `PricingContext` constructor that needs the discount-tier change from task 004" is useful.
- **Lead with state, not narrative.** The next executor doesn't need your debugging journey; they need to know what they'll find when they `git diff` and `git status`.
- **Next steps are an ordered checklist, not a wish list.** Each item should be actionable on its own.
- **Empty fields are fine.** If there are no open questions, leave that line as `Open questions: none`. Don't pad.

## Step 4 — Confirm with the user before writing

Show the user the full draft inline (just print the markdown). Then use AskUserQuestion to confirm:

- **Accept as written.** Proceed to Step 5 with this draft.
- **Edit before writing.** Ask the user (via free-text "Other" or follow-up question) what to change, fold their changes in, then re-show and ask again. Iterate until they accept.
- **Cancel.** Stop without writing anything. Print "Handoff cancelled. No changes made." and exit.

The user owns the handoff. Don't ship a draft they haven't seen.

## Step 5 — Write the task file

Edit the task file in two places:

**Frontmatter:** add (or update) `handoff_at: <YYYY-MM-DD>`. Keep `status: in-progress` and all other fields untouched. Add the field if it doesn't exist; update the date if it does.

**Body:** append the accepted draft section. Placement rules:
- Above any existing `## Implementation summary` and `## Verifier notes`.
- Below `## Task`, `## Implementation notes`, `## Out of scope`, and any prior `## Handoff notes — <earlier date>` sections.

Multiple handoffs stack chronologically (each dated), the same way verifier notes and re-execution notes already stack across attempts.

## Step 6 — Commit and push the task file

Stage just the task file by path — do NOT `git add .` or `git add -A`. The user's in-flight implementation changes stay uncommitted by design (the handoff describes them; the next executor inherits them via the branch state).

```
git add .pm/<slug>/<active_version>/tasks/<NNN>-<task-slug>.md
git commit -m "Handoff task <NNN>: <task title>"
git push origin <branch>
```

If `git commit` reports nothing to commit (e.g. the user re-ran handoff with no changes), surface that and exit cleanly without a Step 7 confirmation. If push fails (remote diverged, etc.), STOP and surface the error verbatim — don't force-push.

## Step 7 — Jira sync (optional, best-effort)

Run this block ONLY if all of:

1. `.pm/<slug>/.jira.yml` exists.
2. `command -v acli` and `acli auth status` succeed. Otherwise print once: `Jira sync skipped — acli not available. Run /pm:jira-init for setup.` and skip.
3. The task's `jira_key` is non-empty. Otherwise skip silently.

If enabled, add a Jira comment to the linked issue with the body of the newly-appended `## Handoff notes — <date>` section (everything below the header). Do **not** transition the issue's status — a handoff isn't a workflow state change; ownership and status are unchanged.

On any `acli` error, print ONE line: `Jira sync skipped for task <NNN> (acli error: <message>). Use /pm:jira-sync to retry.` Continue — do NOT roll back the handoff.

## Step 8 — Print confirmation and next-step hint

```
Handoff recorded for task <NNN> — <title>
  From:      <name> <email>
  Branch:    <branch>  (task file pushed; implementation changes left uncommitted)
  Status:    in-progress  (unchanged)
  Jira:      <jira_key> → comment added   (or "—" if not linked, or "skipped" on error)

Next:
  - To resume this yourself later:        /pm:resume <slug> <NNN>
  - For a teammate to take over cleanly:  /pm:claim <slug> <NNN> --force  (from their machine)
```

## Output discipline

- **Task file only on the commit.** Never stage or commit implementation changes during a handoff — those belong to the next executor's `/pm:execute` session. If you somehow have other paths staged, unstage them before committing.
- **Status stays `in-progress`.** A handoff is context-passing, not a state change. Don't touch `assignee` or `branch` either.
- **No new files, no sidecar artifacts.** Everything lives in the task body. The task file remains the single canonical artifact for the task.
- **Don't auto-run anything next.** No automatic `/pm:resume` or `/pm:claim --force` — those are deliberate actions taken later by the next executor.
- **If the user cancels in Step 4, leave zero side effects.** No frontmatter changes, no commit, no push.

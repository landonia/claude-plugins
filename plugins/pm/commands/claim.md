---
description: Claim a task for yourself — creates the branch, flips status to in-progress, sets assignee, commits and pushes so the claim is visible to teammates.
model: sonnet
argument-hint: [slug] [task-id] [--force]
---

# /pm:claim — Claim a task

You are running the `/pm:claim` command. The user is taking ownership of a task in a multi-developer setting. This command makes the claim **visible to teammates via git** so others won't pick the same task.

## Inputs

Parse `$ARGUMENTS`. Supported forms:
- 0 args → active project, auto-pick next ready task.
- 1 arg slug → that project, auto-pick next ready task.
- 1 arg task id (numeric, 3 digits) → active project, that task.
- 2 args → slug and task id.
- `--force` flag (anywhere in args) → allow taking over a task already claimed by someone else.

## Step 1 — Resolve project, version, and task

Standard active-project resolution. Read `active_version` from prd.md frontmatter.

**Auto-pick next ready task:**
1. List task files in `.pm/<slug>/<active_version>/tasks/` sorted by id ascending.
2. A task is "ready" if status is `pending` or `rejected` AND every `depends_on` id has status `done`.
3. Pick the lowest-id ready task. If none, tell the user and stop.

**Explicit id:**
- If the task's `depends_on` includes a task not `done`, warn and ask before proceeding.
- If the task is already `done` or `done-pending-verify`, refuse — you don't claim completed work.

## Step 2 — Pre-flight checks

Run these in parallel and gather results before doing anything destructive:

1. **Git identity available.** `git config user.name` and `git config user.email` must both return non-empty values. If either is empty, refuse with: "Set `git config user.name` and `git config user.email` first." The assignee will be `<name> <email>`.
2. **Working tree clean.** `git status --porcelain` must be empty. If dirty, refuse with: "You have uncommitted changes. Stash or commit them before claiming a task." (We're about to make a commit; we don't want to commit unrelated work.)
3. **On a sensible base.** The current branch should typically be `main` (or `master`). If on another `pm/<slug>/<id>-...` branch, that's fine — you're switching tasks. If on an unrelated feature branch, warn the user before proceeding.
4. **Remote exists.** `git remote get-url origin` must succeed. Refuse if no remote — there's no team to make the claim visible to.
5. **Pull latest** of the base branch (typically `main`) before reading task state. This is critical — claims race on stale state. Use `git fetch origin && git merge --ff-only origin/main` (or current base), and if FF-only fails, refuse and tell the user to resolve the divergence first.

## Step 3 — Re-read task state from the freshly pulled tree

After pulling, re-read the task file. The state may have changed since the user invoked the command (someone else may have claimed it).

Check the task's `assignee` frontmatter field:
- **Empty / missing** → proceed.
- **Set, matches current git user** → idempotent, tell the user they already own this task, then re-confirm/refresh branch state (skip to Step 5 with the existing branch).
- **Set, different from current user** → REFUSE unless `--force` was passed. Message:
  ```
  Task <NNN> is already claimed by <assignee> (since <claimed_at>).
  Branch: <branch>
  Re-run with --force to take over (recommended only for handoffs).
  ```

If `--force` is passed AND the task is claimed by someone else, proceed but warn loudly and require the user to confirm via AskUserQuestion before continuing.

## Step 4 — Create / switch to the task branch

Branch name: `pm/<slug>/<NNN>-<task-slug>` where `<task-slug>` is derived from the task filename stem after the id (e.g. `001-set-up-schema.md` → `set-up-schema`).

- If branch doesn't exist: `git checkout -b <branch>` from current HEAD.
- If branch exists locally: `git checkout <branch>`.
- If branch exists on remote but not locally: `git checkout -b <branch> origin/<branch>`.

## Step 5 — Update the task file

Edit the task frontmatter:
- `status: in-progress`
- `assignee: <git user.name> <<git user.email>>`
- `branch: <branch>`
- `claimed_at: <YYYY-MM-DD>`

Don't touch any other frontmatter fields. Don't modify the task body.

If `assignee`, `branch`, or `claimed_at` fields don't exist in the frontmatter, add them. If they exist (from a prior claim being overridden via --force), update them.

## Step 6 — Commit and push

Stage just the task file:
```
git add .pm/<slug>/<active_version>/tasks/<NNN>-<task-slug>.md
git commit -m "Claim task <NNN>: <task title>"
git push -u origin <branch>
```

If push fails (typically because the branch diverged on the remote), STOP and surface the error to the user. Don't force-push. The user resolves and re-runs.

## Step 7 — Jira sync (optional, best-effort)

Run this block ONLY if all of these are true; otherwise skip silently or with a single warning:

1. `.pm/<slug>/.jira.yml` exists.
2. `command -v acli` succeeds AND `acli auth status` succeeds. If either fails, print once: `Jira sync skipped — acli not available. Run /pm:jira-init for setup.` and skip the rest of this step.
3. The task's `jira_key` is non-empty. If empty, skip silently (task is not linked to a Jira issue).

If enabled, load `status_mapping` and the extras from `.jira.yml`, then:

- **Transition the issue** to `status_mapping.claim`. Use `acli` to perform the workflow transition. If the issue is already in that status, no-op silently.
- **If `sync_assignee_on_claim` is `true`:** look up the Jira account by the current `git config user.email` and set the issue's assignee. If no Jira account matches the email, print one line: `Jira assignee not set for task <NNN> — no account matches <email>.` and continue.

On any `acli` error during this step, print ONE line: `Jira sync skipped for task <NNN> (acli error: <message>). Use /pm:jira-sync to retry.` Do NOT roll back any pm state. The claim succeeded on the pm side; the Jira side is just a mirror.

## Step 8 — Print confirmation and next-step hint

```
Claimed task <NNN> — <title>
  Assignee:  <name> <email>
  Branch:    <branch>  (pushed to origin)
  Status:    in-progress
  Jira:      <jira_key> → <jira status>   (or "—" if not linked, or "skipped" on error)

Next: /pm:execute <slug> <NNN>
```

## Output discipline

- Never force-push. If the remote rejects, the user resolves.
- Don't commit anything other than the task file. If you somehow have other staged or unstaged changes, that's a pre-flight bug — refuse rather than commit them.
- Don't run `/pm:execute` automatically. Claiming and executing are separate steps so the user can pause between them.
- If the user runs `/pm:claim` from a CI environment (no interactive shell, automation context), it should still work — all decisions either have safe defaults or are flagged via `--force`.

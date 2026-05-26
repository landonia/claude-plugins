---
description: Switch back to a task's branch and pull latest. Used to come back to a task after working on something else (e.g. addressing PR comments or a verify rejection).
model: sonnet
argument-hint: [slug] [task-id]
---

# /pm:resume — Switch back to a task's branch

You are running the `/pm:resume` command. The user is returning to work on a task whose branch they're no longer on.

## Inputs

Parse `$ARGUMENTS`:
- 0 args → active project, list the user's claims (or all in-progress tasks if no claims) and ask which to resume.
- 1 arg slug → that project, same list-and-ask.
- 1 arg task id → active project, that task.
- 2 args → slug and task id explicitly.

## Step 1 — Resolve project and version

Standard active-project resolution. Read `active_version` from prd.md frontmatter.

## Step 2 — Pre-flight checks

1. **Working tree clean.** `git status --porcelain` must be empty. If dirty, refuse with: "Uncommitted changes will be lost on branch switch. Stash, commit, or discard them first."
2. **Inside a git repo.** Standard check.

## Step 3 — Pick the task

**Auto-pick (no task id given):**
1. Read all task files in `.pm/<slug>/<active_version>/tasks/`.
2. Filter to tasks whose `assignee` matches the current `git config user.name` + `user.email`, OR whose `status` is `in-progress`, `done-pending-verify`, or `rejected`.
3. Sort by id ascending.
4. If exactly one match: use it (tell the user which).
5. If multiple: present them with AskUserQuestion — list each with status, assignee, branch, and last-modified date. User picks.
6. If none: tell the user "No tasks to resume. Use /pm:claim to start one, or /pm:status to see project state."

**Explicit task id:**
- Verify the task exists. If not, error clearly.
- If task `status` is `done` (already complete) and `pr_url` is set: warn the user the task is done and PR'd; ask whether to resume anyway (e.g. to address PR comments). Default: yes.
- If task `status` is `pending`: refuse with "Task <NNN> hasn't been claimed yet. Use /pm:claim <slug> <NNN> to start it."

## Step 4 — Find the branch

Read the task's `branch:` frontmatter field.

- **Empty/missing** → refuse with: "Task <NNN> has no branch recorded. It may have been worked on without /pm:claim. Run /pm:claim <slug> <NNN> to set up the branch."
- **Set** → proceed to Step 5.

## Step 5 — Fetch and check out

1. `git fetch origin` — get the latest remote refs.
2. Check whether the branch exists locally (`git rev-parse --verify <branch> 2>/dev/null`).
   - **Local exists:** `git checkout <branch>`.
   - **Remote exists, local doesn't:** `git checkout -b <branch> origin/<branch>`.
   - **Neither exists:** error with: "Branch `<branch>` not found locally or on origin. The branch may have been deleted after merge — task is effectively complete. To re-open, claim a new task."
3. Pull latest on the branch: `git merge --ff-only origin/<branch>` if the remote branch exists. If FF-only fails (the remote branch has diverged from your local copy), STOP and surface the conflict. Don't merge blindly.

## Step 6 — Print task state and next-step hint

Print:

```
Resumed task <NNN> — <title>
  Branch:    <branch>  (pulled latest)
  Status:    <status>
  Assignee:  <assignee>
  PR:        <pr_url or "—">
```

Then a context-aware next-step hint based on status:

- **`in-progress`** → "Next: continue with /pm:execute <slug> <NNN> (or /pm:complete <slug> <NNN> if the work is already verified)."
- **`done-pending-verify`** → "Next: /pm:verify <slug> <NNN>."
- **`rejected`** → "Next: /pm:execute <slug> <NNN> — address the Verifier notes" + print the most recent `## Verifier notes` section.
- **`done`** with `pr_url` set → "Next: address PR comments locally, commit, then `git push` to update the PR. (Or /pm:complete <slug> <NNN> if you want to re-record the PR URL after fixes.)"

## Output discipline

- Read-only on the task file. Don't change `status`, `assignee`, or any other field — resuming is a navigation action, not a state change.
- Don't pull main, don't fetch tags, don't do anything beyond fetching and checking out the task branch.
- If `git checkout` fails (uncommitted changes you didn't catch in pre-flight, branch lock, etc.), surface the error exactly as git reported it.

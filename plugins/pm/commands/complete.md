---
description: Mark a verified task as complete — commits remaining changes, pushes, opens a PR via gh, and records the PR URL on the task.
argument-hint: [slug] [task-id] [--checkout-main]
---

# /pm:complete — Open the PR for a verified task

You are running the `/pm:complete` command. The user is declaring a task fully done and ready for human review / merge. This command commits any remaining implementation changes, pushes, and opens a pull request — the PR description is the task file itself.

## Inputs

Parse `$ARGUMENTS`. Supported forms:
- 0 args → active project, auto-pick lowest-id task with `status: done` and empty `pr_url`.
- 1 arg slug → that project, same auto-pick.
- 1 arg task id → active project, that task.
- 2 args → slug and task id.
- `--checkout-main` flag (anywhere) → after the PR is opened, pull latest main and switch to it. Default: stay on the task branch.

## Step 1 — Resolve project, version, and task

Standard active-project resolution. Read `active_version` from prd.md frontmatter.

For auto-pick: a task is "complete-ready" if `status: done` AND `pr_url` is empty/missing. If none, tell the user: "No verified tasks awaiting PR. Run /pm:verify first, or check /pm:status."

If the user names a task explicitly, verify it's actually ready:
- If `status` is `done-pending-verify` → refuse with "Task <NNN> hasn't been verified yet. Run /pm:verify first."
- If `status` is `in-progress` or `pending` → refuse with "Task <NNN> isn't done — implementation isn't complete."
- If `status` is `rejected` → refuse with "Task <NNN> was rejected. Run /pm:execute to address Verifier notes."
- If `status` is `done` and `pr_url` is already set → tell the user the PR already exists at `<pr_url>`, ask whether to push latest commits to update it (yes) or skip (no).

## Step 2 — Pre-flight checks

Run in parallel where possible:

1. **`gh` is installed.** `command -v gh` must succeed. If not, refuse with: "GitHub CLI (`gh`) not found. Install it from https://cli.github.com/ then re-run."
2. **`gh` is authenticated.** `gh auth status` must succeed. If not, refuse with: "Not authenticated to GitHub. Run `gh auth login` then re-run."
3. **On the right branch.** Read the task's `branch:` frontmatter field. `git rev-parse --abbrev-ref HEAD` must equal it. If on the wrong branch, suggest `/pm:resume <slug> <NNN>` to switch first.
   - If the task has no `branch:` set (task was never `/pm:claim`-ed), check whether the current branch is sensible (not main/master). If yes, set `branch:` to the current branch and continue. If on main, refuse with: "You're on main. Task <NNN> has no branch recorded. Run /pm:claim or switch to the task branch."
4. **Remote exists** for this branch. `git remote get-url origin` must succeed.

## Step 3 — Commit any uncommitted changes

Run `git status --porcelain`. If anything is uncommitted:

- Stage everything: `git add -A` (the verifier already reviewed these changes, so they're known-good).
- Commit with message: `Task <NNN>: <task title>` (subject line, no body). Use `git commit -m "..."` with the message via heredoc.

If the working tree is already clean, skip to Step 4.

## Step 4 — Push the branch

`git push -u origin <branch>`. If push fails (typically because the remote diverged), STOP and surface the error. Don't force-push. The user resolves and re-runs.

## Step 5 — Open or update the PR

Detect whether a PR already exists for this branch: `gh pr view --json url,state 2>/dev/null`.

**If no PR exists:**

Build the PR title from the task: `Task <NNN>: <task title>`.

Build the PR body from the task file contents — strip the YAML frontmatter, keep the Markdown body. Prepend a small header:

```markdown
**Project:** <slug>  |  **Version:** <active_version>  |  **Task:** <NNN>

This PR implements task <NNN> from `.pm/<slug>/<active_version>/tasks/<NNN>-<task-slug>.md`. The task file in this PR is its own description — see acceptance criteria, PRD/research refs, implementation summary, and verifier notes below.

---

```

Then append the task body (Task description, Implementation notes, Out of scope, Implementation summary, Verifier notes).

Run `gh pr create --title "<title>" --body-file <tempfile>`. Capture the PR URL from the output.

**If a PR already exists** (status is `done` and `pr_url` was already set, or `gh pr view` succeeded):

- The push in Step 4 already updated the PR's commits. Don't re-create.
- Recover the PR URL from `gh pr view --json url`.

## Step 6 — Record PR URL on the task

Edit the task file's frontmatter to add/update:
- `pr_url: <url>`
- `completed_at: <YYYY-MM-DD>`

Commit this single change with message: `Task <NNN>: record PR URL`. Push.

## Step 7 — Optional checkout-main

If `--checkout-main` was passed:

1. `git fetch origin`.
2. `git checkout main` (or `master` if that's the default — detect via `git symbolic-ref refs/remotes/origin/HEAD`).
3. `git merge --ff-only origin/main` (or origin/master). If FF-only fails, warn the user that main has diverged and skip the merge — they're on main but not on the latest.

If not passed, stay on the task branch (the user may need to address PR comments).

## Step 8 — Print confirmation and next-step hint

```
Task <NNN> — complete.
  PR:        <pr_url>
  Branch:    <branch>  (still checked out  | switched to main)
  Status:    done
  Recorded:  pr_url, completed_at

Next: human review on the PR. After merge:
  /pm:claim <slug>     to pick up the next task
  (or /pm:release <slug> if all tasks are done and merged)
```

If `--checkout-main` was passed, adjust the message — you're already on main, ready for the next claim.

If verify ever rejects this task again after the PR is open (e.g. someone runs /pm:verify on the PR branch), the status flips to `rejected`. Run `/pm:resume <slug> <NNN>` to come back to the branch, `/pm:execute <slug> <NNN>` to address the new Verifier notes, then `/pm:complete <slug> <NNN>` to push the fixes (which updates the open PR automatically).

## Output discipline

- Don't force-push. Ever.
- Don't merge the PR. That's a human decision (or your team's auto-merge bot's).
- Don't delete the branch. The PR may not be merged yet, and the task may need follow-up work.
- Don't add labels, reviewers, or milestones to the PR. Those are team conventions — leave them to the user's PR template or follow-up commands.
- If `gh pr create` fails (network issue, GitHub down, branch protection rejection), surface the error and tell the user the branch is pushed and they can open the PR manually.

---
description: Print a project dashboard — PRD title, version state, task counts, next ready task, blockers.
argument-hint: [slug]
---

# /pm:status — Project dashboard

Read-only summary of a project's state.

## Inputs
- Slug: `$ARGUMENTS` (active-project resolution if empty).

## Step 1 — Resolve project

Standard resolution. If no project, tell the user "No projects in .pm/. Start one with /pm:prd <idea>."

## Step 2 — Gather state

Read:
- `prd.md` frontmatter (title, status, active_version, created).
- For EACH version folder `vN/`:
  - `goals.md` frontmatter (status).
  - Whether `RELEASE.md` exists.
  - Count of research files in `research/` (excluding `_index.md` and `.archive/`).
  - Task counts in `tasks/` by status: pending / in-progress / done-pending-verify / done / rejected.
- For the **active version**, also collect each task's `assignee`, `branch`, `claimed_at`, `jira_key`, and `pr_url` fields where present.
- For the **active version's** `goals.md`, also read `jira_epic` if present.
- Detect Jira enablement: `.pm/<slug>/.jira.yml` exists. If yes, read `site` from it (for building Jira URLs in output).

Compute "next ready task" for the active version: lowest-id task with status `pending` or `rejected` whose deps are all `done`.

Count amendments in `prd.md` `## Amendments` section.

## Step 3 — Print the dashboard

Format:

```
<Title> (<slug>)
Status: <status>   Active version: <active_version>   Created: <date>   Amendments: <count>

Versions:
  v1  shipped  (released <date>)   — 12 tasks, 4 research reports
  v2  active                       — 3/8 tasks done, 1 rejected, 1 in-progress
  v3  planning                     — 0 tasks

Active version detail (v2):
  Research:  6 personas — see .pm/<slug>/v2/research/_index.md
  Tasks:     pending: 4   in-progress: 1   done-pending-verify: 0   done: 2   rejected: 1
  Blockers:  task 005 (rejected) — see Verifier notes
             task 007 (pending) blocked by 005
  Jira:      enabled — site company.atlassian.net   epic PROJ-100 (In Progress)

In-progress / claimed tasks:
  ID   Title                          Assignee              Branch                         Claimed     Jira
  004  Add billing webhook handler    Alice <a@example.com> pm/<slug>/004-billing-webhook  2026-05-22  PROJ-123

Next ready task: 006 — "Wire up dunning email templates"
Suggested next command: /pm:claim <slug>   (then /pm:execute)
```

Conditional sections:
- If no tasks have assignees set, omit the "In-progress / claimed tasks" section entirely. If the user is solo (only one assignee value appears across all tasks, matching git config user), still show the section — it's useful for the user to see their own claims.
- The `Jira:` line in "Active version detail" appears ONLY if `.pm/<slug>/.jira.yml` exists. The epic portion appears only if `jira_epic` is set in the active version's goals.md.
- The `Jira` column in the in-progress table appears ONLY when Jira is enabled. Tasks without a `jira_key` show `—` in the column.
- When Jira is enabled, render the jira_key as a clickable URL in the output if the terminal/renderer supports it: `https://<site>/browse/<KEY>`.

If the active version has no tasks yet: "Next: /pm:plan <slug>".
If the active version has no research yet: "Next: /pm:research <slug>".
If everything in active version is done and no RELEASE.md: "Next: /pm:release <slug>".

## Output discipline
- This command WRITES NOTHING. Read-only.
- Keep it scannable. The user is using this as a quick check, not a deep dive.

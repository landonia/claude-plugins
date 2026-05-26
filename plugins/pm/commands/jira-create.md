---
description: Create a new Jira issue from a pm task (or batch-create for all unlinked tasks). Records the issue key on the task.
argument-hint: <slug> [task-id]
---

# /pm:jira-create — Create new Jira issue(s)

You are running the `/pm:jira-create` command. The user wants new Jira issue(s) created from pm task(s). If a task id is given, only that task. Otherwise, batch-create for every unlinked task in the active version.

## Inputs

Parse `$ARGUMENTS`:
- 0 args → active project, batch mode.
- 1 arg slug → that project, batch mode.
- 1 arg task id → active project, single task.
- 2 args → slug and task id.

## Step 1 — Resolve project, version

Standard active-project resolution. Read `active_version` from prd.md frontmatter.

## Step 2 — Jira preflight

Required:
- `.pm/<slug>/.jira.yml` exists. If not, refuse with: "Jira not enabled for <slug>. Run /pm:jira-init first."
- `acli` installed and authenticated. Same refusal pattern as /pm:jira-init.

Load `.jira.yml`. Read: `site`, `project_key`, `default_issue_type`, `epic_issue_type`.

## Step 3 — Determine the parent epic (if any)

Read `.pm/<slug>/<active_version>/goals.md` frontmatter. If `jira_epic` is set, use it as the parent for all created issues.

If `jira_epic` is empty AND Jira is enabled, offer to create the epic first (mirrors the epic-creation block in /pm:version). If the user declines, proceed without a parent.

## Step 4 — Pick target tasks

**Single-task mode (task id given):**
- Refuse if the task already has a non-empty `jira_key` (suggest /pm:jira-link to change it).

**Batch mode:**
- List every task in `<active_version>/tasks/` whose `jira_key` is empty.
- Sort by id ascending.
- Show the list to the user with AskUserQuestion (multiSelect, default = all selected) so they can deselect any task they don't want a Jira for.
- If the list is empty, tell the user "All tasks already linked." and stop.

## Step 5 — Create each issue

For each target task, run `acli` to create an issue with:
- **Summary** = the task's frontmatter `title`.
- **Description** = the task's body content (Task, Implementation notes, Out of scope sections — exclude Implementation summary and Verifier notes since those are post-execute). Strip pm internal references that won't make sense in Jira context.
- **Issue type** = `default_issue_type` from `.jira.yml`.
- **Parent** = `jira_epic` if set (use the appropriate `acli` flag for epic parent).
- **Labels** = `["pm-<slug>", "<active_version>"]`.

Show the rendered fields for the FIRST issue to the user as a preview before creating, with options:
- **Looks good, create this one and all the others without further prompts.**
- **Edit fields before creating (and ask again for each).**
- **Cancel.**

For batch mode, proceed to create the rest after the preview-approval.

## Step 6 — Record `jira_key` on each task

For each successfully created issue, edit the task frontmatter to set `jira_key: <new-key>`. Don't touch other fields.

If a creation fails (network, permission, validation), record nothing on that task and continue with the next. Collect failures.

## Step 7 — Push current status to Jira

For each newly-created issue, if the task's pm status is not the Jira issue's default initial status (which is usually "To Do" / equivalent), push a status transition via `/pm:jira-sync` semantics for that task. Skip if pm status is `pending` (Jira's initial state should already match).

## Step 8 — Hand off

Print a summary:
```
Created <N> Jira issue(s):
  <NNN> "<title>"       → <ISSUE-KEY>   https://<site>/browse/<KEY>
  <NNN> "<title>"       → <ISSUE-KEY>   https://<site>/browse/<KEY>
  ...

Failed: <M>
  <NNN> "<title>"       — <reason>

Next: /pm:status <slug>
```

If single-task mode and successful, simpler one-line confirmation.

## Output discipline

- One Jira call per task. Don't batch in a single multi-create call — if one fails, the others should still succeed.
- Never overwrite an existing `jira_key`. Refuse if a task already has one.
- Don't push verifier notes or implementation summary into the description — those are populated after execution and don't belong in initial issue creation.
- The labels (`pm-<slug>`, version) are how status syncs can find the issue group later — keep them stable.

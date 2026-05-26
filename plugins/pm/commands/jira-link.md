---
description: Attach an existing Jira issue to a pm task. Sets `jira_key` in the task frontmatter.
argument-hint: <slug> [task-id] <ISSUE-KEY>
---

# /pm:jira-link — Attach existing Jira issue

You are running the `/pm:jira-link` command. The user has an existing Jira issue (e.g. created in a planning meeting) and wants to link it to a pm task.

## Inputs

Parse `$ARGUMENTS`. The issue key looks like `PROJ-123` (uppercase project prefix + dash + number). Disambiguate from the slug and task id by pattern:
- 1 arg matching `^[A-Z][A-Z0-9_]+-[0-9]+$` → that's the issue key; active project; auto-pick a task (latest unlinked).
- 2 args, one matches issue key pattern → other is slug or task id.
- 3 args → slug, task id, issue key in that order.

If the issue key is missing, refuse with usage hint.

## Step 1 — Resolve project, version, and task

Standard active-project resolution. Read `active_version` from prd.md frontmatter.

For auto-pick task: lowest-id task in the active version whose `jira_key` is empty. If none, tell the user "All tasks already linked. Use /pm:jira-create for new tasks or /pm:status to review."

## Step 2 — Jira preflight

Required:
- `.pm/<slug>/.jira.yml` exists. If not, refuse with: "Jira not enabled for <slug>. Run /pm:jira-init first."
- `acli` installed and authenticated. If either fails, refuse with remediation hint (see /pm:jira-init for exact wording).

## Step 3 — Validate the Jira issue

Run `acli jira issue view <ISSUE-KEY>` (or the actual command shape) to confirm:
- The issue exists.
- It belongs to the configured `project_key` from `.jira.yml`. If a different project, warn the user and ask whether to link anyway.

If the lookup fails (404, network), refuse with the acli error message.

## Step 4 — Check for existing link

If the task already has a non-empty `jira_key`:
- If it matches the new key, tell the user it's already linked and stop.
- If it's different, ask whether to overwrite. Default: no.

Also check whether any OTHER task in the active version is already linked to this issue (`grep` `jira_key: <KEY>` across `tasks/*.md`). If yes, warn — a single Jira issue linked to multiple tasks is usually a mistake. Ask whether to proceed.

## Step 5 — Update the task file

Edit the task frontmatter: set `jira_key: <ISSUE-KEY>`. Do not touch any other field.

## Step 6 — Push current status to Jira

If the task's current pm `status` has a configured Jira transition target (i.e. it's `in-progress`, `done-pending-verify`/`done`, etc.), push the appropriate transition so the linked issue reflects pm reality. Use the same logic as `/pm:jira-sync` for a single task — call into that code path. If sync fails, warn and continue (don't roll back the link).

## Step 7 — Hand off

Print:
```
Linked task <NNN> ("<title>") to <ISSUE-KEY>.
  Jira URL: https://<site>/browse/<KEY>
  Status synced: <pm status> → <jira status> (or "skipped: <reason>")

Next: /pm:status <slug>
```

## Output discipline

- Don't create Jira issues — that's `/pm:jira-create`. If the user passes an issue key that doesn't exist and asks to create it, redirect.
- Don't modify the Jira issue's summary or description to match the pm task. The user may have intentional differences (e.g. a higher-level Jira story covering multiple pm tasks).
- Don't push the current pm status to Jira if it would be a regression (e.g. task is `done` but Jira issue is also `done` — no-op).

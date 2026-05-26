---
description: Set up Jira integration for a project. Writes .pm/<slug>/.jira.yml interactively; verifies acli is installed and authenticated.
model: sonnet
argument-hint: [slug]
---

# /pm:jira-init — Enable Jira for a project

You are running the `/pm:jira-init` command. The user wants to turn on the optional Jira integration for a project. Presence of `.pm/<slug>/.jira.yml` is the on-switch — once written, other pm commands begin best-effort syncing to Jira.

## Inputs
- Slug: `$ARGUMENTS` (active-project resolution if empty).

## Step 1 — Resolve project

Standard active-project resolution. If no project exists, refuse with: "No projects found. Start one with /pm:prd first."

If `.pm/<slug>/.jira.yml` already exists, ask the user:
- **Overwrite** — back up the existing file to `.jira.yml.bak.<timestamp>` and proceed.
- **Edit interactively** — read current values and offer to change each.
- **Cancel.**

## Step 2 — Verify `acli` is installed and authenticated

Run `command -v acli` to detect the binary. If missing, print:
```
acli (Atlassian CLI) is not installed.
Install from: https://developer.atlassian.com/cloud/acli/
Re-run /pm:jira-init after install.
```
Refuse to write config in this case — there's no value in enabling Jira sync we can't perform.

If `acli` is installed, run `acli auth status` (or the equivalent for the installed version). If not authenticated, print the remediation hint (`acli auth login`) and refuse to proceed.

## Step 3 — Gather config interactively

Use AskUserQuestion / free-form prompts:

1. **Site** — Jira Cloud subdomain (e.g. `company.atlassian.net`). Validate it looks like a hostname.
2. **Project key** — uppercase short key, e.g. `PROJ`. Validate by attempting an `acli jira project view --key <key>` (or equivalent) and erroring clearly if the key isn't found.
3. **Default issue type for tasks** — usually `Story` or `Task`. Try `acli jira project view` to list available issue types and present them as choices; default to `Story` if available, otherwise the first non-epic type.
4. **Epic issue type** — usually `Epic`. Same listing approach; default to `Epic`.

## Step 4 — Discover status names from the workflow

Run `acli` to enumerate the workflow statuses available for the chosen issue type (e.g. `acli jira project workflow ...` — adjust to the actual command shape). Seed the status mapping with sensible guesses:

- `claim` → first status that contains "Progress" (e.g. "In Progress")
- `verify_accept` → first status that contains "Review" (e.g. "In Review"), fall back to "In Progress" if none
- `verify_reject` → same as `claim` (revert to In Progress)
- `complete` → same as `verify_accept`
- `release_epic` → first status that looks like "Done" / "Closed"

Show the guesses to the user and let them edit each value before writing. If the workflow lookup fails, fall back to defaults of `"In Progress"`, `"In Review"`, `"In Progress"`, `"In Review"`, `"Done"`.

## Step 5 — Ask about the extras

Use AskUserQuestion for both:
- `post_pr_comment_on_complete` — when /pm:complete opens a PR, post the URL as a Jira comment? (default: true)
- `sync_assignee_on_claim` — when /pm:claim runs, set the Jira assignee via email lookup? (default: true)

## Step 6 — Write `.pm/<slug>/.jira.yml`

Format:

```yaml
site: <site>
project_key: <PROJ>
default_issue_type: <Story>
epic_issue_type: <Epic>
status_mapping:
  claim: "<In Progress>"
  verify_accept: "<In Review>"
  verify_reject: "<In Progress>"
  complete: "<In Review>"
  release_epic: "<Done>"
post_pr_comment_on_complete: <true|false>
sync_assignee_on_claim: <true|false>
```

Show the rendered file to the user before writing and let them tweak.

## Step 7 — Optional one-shot follow-ups

Ask (use AskUserQuestion, multiSelect):

- **Create the v1 epic now?** — If the active version has no `jira_epic` in its goals.md, offer to create one. If yes, mirror `/pm:version`'s epic-creation block: create the Jira epic and record `jira_epic:` into `<active_version>/goals.md` frontmatter.
- **Backfill Jira issues for existing tasks?** — If `<active_version>/tasks/` already contains tasks, offer to run `/pm:jira-create <slug>` to batch-create issues for any with empty `jira_key`. If yes, hand off to the same code path used by `/pm:jira-create` (do not duplicate that logic here — call it).

## Step 8 — Hand off

Print:
```
Jira enabled for <slug>.
  Site:           <site>
  Project:        <PROJ>
  Config:         .pm/<slug>/.jira.yml
  Active epic:    <PROJ-NNN (or "—")>
  Linked tasks:   <count>/<total>

From now on /pm:claim, /pm:verify, /pm:complete, /pm:version, and /pm:release will sync status to Jira (best-effort).
Next: /pm:jira-create <slug>   (if any tasks are unlinked)
      /pm:status <slug>        (see project state)
```

## Output discipline

- Never write credentials to `.jira.yml`. Auth is `acli`'s responsibility.
- Refuse if `acli` is missing or unauthenticated. There's no point enabling Jira sync we can't perform.
- If a workflow lookup fails (Jira down, permission issue), fall back to defaults — don't refuse to write the file.
- The file is committable. Mention this to the user so they decide whether to add it to .gitignore (recommended only if site/project_key are considered sensitive).

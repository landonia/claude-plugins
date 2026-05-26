---
description: Peek at the next ready task without executing it.
model: haiku
argument-hint: [slug]
---

# /pm:next — Peek at next ready task

Read-only — shows which task `/pm:execute` would pick next.

## Inputs
- Slug: `$ARGUMENTS` (active-project resolution).

## Step 1 — Resolve project and active version

Standard resolution. Read `active_version` from prd.md frontmatter.

## Step 2 — Find next ready task

Apply the same algorithm as `/pm:execute` Step 1:
1. List task files in `.pm/<slug>/<active_version>/tasks/` sorted by id.
2. A task is "ready" if status is `pending` or `rejected` AND every `depends_on` id has status `done`.
3. Pick the lowest-id ready task.

If none:
- All done? Print "All tasks complete. Suggested: /pm:release <slug>."
- Some pending but all blocked? Print the blocked tasks and what's blocking them.
- No tasks at all? Print "No tasks. Suggested: /pm:plan <slug>."

## Step 3 — Print the task

Format:

```
Next ready task: <NNN> — <title>
Status: <pending|rejected>
Depends on: <list of ids or "—">
PRD refs: <list>
Research refs: <list>
Jira: <jira_key>  (or "—" if not linked; only shown when .pm/<slug>/.jira.yml exists)
Acceptance criteria:
  - <criterion 1>
  - <criterion 2>

<First 3-5 lines of the task body for context>

Run with: /pm:claim <slug> <NNN>     (recommended in multi-dev — makes the claim visible)
         /pm:execute <slug> <NNN>   (skips claiming — fine for solo work)
```

If the task is `rejected`, also show the most recent `## Verifier notes` section so the user can see what needs addressing.

## Step 4 — Also surface in-progress tasks

After printing the next ready task, ALSO print any tasks currently `in-progress` with their assignees, so the user can see who's working on what:

```
Currently in progress:
  002  Add billing webhook handler    Alice <a@example.com>  branch pm/<slug>/002-billing-webhook  since 2026-05-22  PROJ-123
  005  Wire up dunning emails         Bob <b@example.com>    branch pm/<slug>/005-dunning-emails   since 2026-05-23  PROJ-127
```

Omit this section entirely if no tasks are `in-progress`. Append the `jira_key` column only when `.pm/<slug>/.jira.yml` exists; show `—` for tasks without a key.

## Output discipline
- Read-only.
- Don't flip any status. Don't write anything.

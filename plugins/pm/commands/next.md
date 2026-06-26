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

Apply the same algorithm as `/pm:execute` Step 1, **including its Step 1.4 Claim discovery** (read `${CLAUDE_PLUGIN_ROOT}/commands/execute.md` Step 1.4 — keep in sync):
1. List task files in `.pm/<slug>/<active_version>/tasks/` sorted by id.
2. A task is "ready" if status is `pending` or `rejected` AND every `depends_on` id has status `done`.
3. Run Claim discovery and drop ready tasks **actively claimed by someone else**. Pick the lowest-id surviving ready task.

If ready tasks exist but ALL are claimed by others, say so and list each task's owner (from the discovered claims) instead of recommending one.

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

## Step 4 — Also surface claimed / in-progress tasks

After printing the next ready task, ALSO print every **active claim** from Step 1.4's
`claimsByStem` (NOT the working-tree `in-progress` status — claims live on their branches), so the
user can see who's working on what. Use the task title from the local task file and the
assignee/branch/claimed_at/jira_key from the discovered claim record:

```
Currently in progress:
  002  Add billing webhook handler    Alice <a@example.com>  branch pm/<slug>/002-billing-webhook  since 2026-05-22  PROJ-123
  005  Wire up dunning emails         Bob <b@example.com>    branch pm/<slug>/005-dunning-emails   since 2026-05-23  PROJ-127
```

Omit this section entirely if there are no active claims (or discovery was skipped and no local task is `in-progress`). Append the `jira_key` column only when `.pm/<slug>/.jira.yml` exists; show `—` for tasks without a key.

## Output discipline
- Read-only.
- Don't flip any status. Don't write anything.

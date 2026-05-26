---
description: Regenerate pending tasks from an amended PRD while preserving done tasks.
model: opus
argument-hint: <slug>
---

# /pm:replan — Regenerate pending tasks

You are running the `/pm:replan` command. The PRD has changed (typically via `/pm:amend`) and pending tasks may no longer match.

## Inputs
- Slug: `$ARGUMENTS` (active-project resolution if empty).

## Step 1 — Resolve project and active version

Same as other commands. Read `active_version` from prd.md frontmatter.

## Step 2 — Inventory existing tasks

Read every file in `.pm/<slug>/<active_version>/tasks/`. Partition by status:
- **Preserved (do not touch):** `done`, `done-pending-verify`, `in-progress`
- **Candidates for replacement:** `pending`, `rejected`

If there are no candidates, stop and tell the user "Nothing to replan — no pending or rejected tasks."

## Step 3 — Read updated context

Read the full current state:
- `prd.md` (including Amendments)
- `<active_version>/goals.md`
- All files in `<active_version>/research/`
- The bodies of the preserved tasks (so the new plan knows what's already done and doesn't redo it)

## Step 4 — Draft the new pending plan

Decompose the remaining work in light of:
- What's already done (don't redo it).
- The amended PRD goals.
- Updated research findings (especially any "Update —" sections from `/pm:rerun-research`).
- Verifier notes on any `rejected` tasks — those gaps must be addressed.

Generate new task definitions for the remaining work. Use the next free ID (continue from the highest existing ID; don't reuse IDs from candidates being replaced).

Present a diff-style preview to the user before writing:

```
Preserving (X tasks): 001, 002, 003 (done)
Replacing (Y tasks): 004 (pending), 005 (rejected) → archiving
Adding (Z tasks): 006, 007, 008, 009
```

Use AskUserQuestion to confirm. Let the user adjust which candidates to actually replace (some pending tasks may still be valid).

## Step 5 — Archive replaced tasks

For each task being replaced:
- Move its file to `.pm/<slug>/<active_version>/tasks/.archive/<NNN>-<slug>-<timestamp>.md`.
- Don't delete — the archive preserves history and any partial work the executor may have started.

## Step 6 — Write new tasks

Use the same file format as `/pm:plan` Step 5. Make sure `depends_on` references account for the new ID layout. If a new task depends on a preserved task that's already `done`, that's fine — `depends_on` just needs the ID; status filtering happens at execute time.

## Step 7 — Hand off

Print:
- Counts: preserved / archived / added.
- The first ready task post-replan.
- Next-step hint: `/pm:execute <slug>` or `/pm:status <slug>` to review.

## Output discipline
- NEVER touch tasks with status `done`, `done-pending-verify`, or `in-progress`. Even if the amendment seems to invalidate them, that work is captured and the verifier already approved it (or is about to).
- If the amendment fundamentally invalidates done work, that's a `/pm:version <slug> v2` situation, not a replan. Tell the user.

---
description: List all projects in .pm/ with a one-line state summary each.
---

# /pm-list — List all projects

Read-only listing of every project under `.pm/`.

## Step 1 — Scan

List every direct subdirectory of `.pm/` that contains a `prd.md` (skip hidden folders, skip `.pm/.archive/` if present).

If `.pm/` doesn't exist or is empty, tell the user "No projects yet. Start one with /pm-prd <idea>." and stop.

## Step 2 — Summarize each

For each project, read just enough to print one line:
- Title from prd.md frontmatter.
- Status from prd.md frontmatter (drafting / active / shipped / archived).
- Active version.
- Task counts in the active version: done / total.
- Last modification time of the project folder.

## Step 3 — Print

Format:

```
Projects in .pm/:

  recurring-s3-exports         active        v2     5/8 done    updated 2 days ago
  onboarding-revamp            shipped       v1     12/12 done  updated 3 weeks ago
  search-redesign              drafting      v1     0/0 tasks   updated today
  legacy-archive               archived      v1     —            updated last month

3 active, 1 shipped, 1 archived. Use /pm-status <slug> for details.
```

Sort: active first (most recently updated first within the group), then drafting, then shipped (newest first), then archived.

## Output discipline
- Read-only.
- If a `.pm/<slug>/` exists without a prd.md, list it as `<slug>  (no prd.md — corrupt?)` so the user knows it's there but malformed.

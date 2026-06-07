---
description: Append a dated amendment to a project's PRD after research findings, scope changes, or stakeholder input.
model: opus
argument-hint: <slug>
---

# /pm:amend — Add a PRD amendment

You are running the `/pm:amend` command. The user is amending an existing PRD.

## Inputs
- Slug: `$ARGUMENTS` (may be empty — use the active-project resolution rules below).

## Step 1 — Resolve the project

Active-project resolution:
1. If `$ARGUMENTS` names a `.pm/<slug>/` that exists, use it.
2. Else if exactly one `.pm/<slug>/` exists, use that one and tell the user.
3. Else if exactly one project has `status: active` in its prd.md frontmatter, use that and tell the user.
4. Else list available slugs from `.pm/*/prd.md` and ask the user to pick.

If no `.pm/` directory exists at all, tell the user "No projects found. Start one with `/pm:prd <idea>`." and stop.

## Step 2 — Gather amendment details

Read `.pm/<slug>/prd.md` so you understand current state.

Ask the user (use AskUserQuestion where discrete choices apply):
1. **What's being amended?** (Short title, e.g. "drop multi-region support from v1")
2. **Why?** (Reason — research finding, stakeholder change, technical discovery, etc.)
3. **What changes?** (The actual delta — what's added, removed, modified)
4. **Does this affect pending tasks?** (yes / no / unsure — drives the next-step hint)

## Step 3 — Append the amendment

Append to the `## Amendments` section of `prd.md`. Format:

```markdown
### <YYYY-MM-DD> — <short title>
**Why:** <one or two sentences>
**Change:** <concrete delta — what sections of the PRD this affects, in observable terms>
**Impact on pending work:** <which tasks/versions are affected, or "none">
```

Insert it as the most recent entry (entries are ordered newest-first under `## Amendments`).

## Step 4 — Show diff and confirm

Before writing, show the user the exact text being appended. Apply any requested edits.

## Step 5 — Hand off

After writing, look at the amendment text and check whether it touches **architecture concerns** — telltale words like "switch from X to Y" (database, queue, framework, hosting), "add a queue", "multi-region", "stateless", "async", "GraphQL", "REST", "tenancy", "auth provider", "horizontal scaling", "microservice", "monolith". If it does, also suggest `/pm:architect <slug>` (amend mode) so the architecture decisions get updated in sync — not just the PRD prose. Likewise, if the amendment touches **testing concerns** — telltales like "coverage", "e2e", "test framework", "flaky", "CI gate", "must be tested" — and `testing.md` exists for the active version, also suggest `/pm:test <slug>` (amend mode).

Then suggest the appropriate next step based on the user's answer to "does this affect pending tasks?":
- **Yes + architecture-touching:** suggest `/pm:architect <slug>` first, then `/pm:replan <slug>` once architecture decisions are updated.
- **Yes:** suggest `/pm:replan <slug>` (regenerates pending tasks from the amended PRD).
- **Unsure:** suggest `/pm:status <slug>` to review current state, then decide.
- **No:** print confirmation and stop.

## Output discipline
- Never rewrite existing PRD sections from this command. Amendments are append-only.
- If the user describes a change so large that it's really a new version (e.g. "actually let's pivot to a totally different product"), surface that and suggest `/pm:version <slug> v2` instead.

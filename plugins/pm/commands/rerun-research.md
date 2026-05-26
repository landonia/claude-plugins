---
description: Re-run a single research persona (useful after PRD amendments or thin output).
argument-hint: <slug> <persona-slug>
---

# /pm:rerun-research — Re-run one persona

You are running the `/pm:rerun-research` command.

## Inputs
Parse `$ARGUMENTS`:
- First token = slug (or empty → active-project resolution).
- Second token = persona slug (the filename stem under research/, e.g. `security-architect`).

If the persona slug is missing, list the personas currently present in `.pm/<slug>/<active_version>/research/` and ask which to re-run.

## Step 1 — Resolve project and version

Same active-project resolution as `/pm:research`. Read `active_version` from prd.md frontmatter.

## Step 2 — Locate persona brief

- If the persona slug matches one in `plugins/pm/personas.md`, use the catalog brief.
- If the persona file exists but isn't in the catalog (ad-hoc), read the existing report's frontmatter or top section to recover the original framing. If that's ambiguous, ask the user to confirm the brief.

## Step 3 — Archive the existing report

Move `.pm/<slug>/<active_version>/research/<persona-slug>.md` to `.pm/<slug>/<active_version>/research/.archive/<persona-slug>-<timestamp>.md` so the prior findings aren't lost.

## Step 4 — Dispatch a single subagent

Spawn ONE Agent call (subagent_type: `general-purpose`) with the same prompt structure as `/pm:research` Step 5, for just this persona. Include:
- The (possibly amended) PRD and current version goals.
- The persona brief.
- The path of the archived prior report, and an instruction: "Read the archived prior report and explicitly call out what's changed in your new findings vs the prior ones."
- The output path for the new report.

## Step 5 — Update the index

After the subagent returns, update `.pm/<slug>/<active_version>/research/_index.md` to reflect the rerun:
- Update the persona's headline.
- Update the "Cross-cutting open questions" section if this persona's open questions changed.
- Add a note: `<persona-slug> last re-run: <YYYY-MM-DD>`.

## Step 6 — Hand off

Print the new report path and the diff in open questions (added/removed/changed) vs the archived version. If open questions changed materially, suggest `/pm:amend` or `/pm:replan` as appropriate.

---
description: Scaffold the next version (vN+1) of a project, with a mini PRD-style interview to capture what's in scope.
model: opus
argument-hint: <slug> <new-version>
---

# /pm:version — Start a new version

You are running the `/pm:version` command. The user wants to start the next milestone (e.g. v2 after v1 shipped).

## Inputs
Parse `$ARGUMENTS`:
- First token = slug (or empty → active-project resolution).
- Second token = new version label (e.g. `v2`, `v2.0`, `2026q3`). REQUIRED.

If the second token is missing, ask: "What's the new version called? (e.g. `v2`)"

## Step 1 — Resolve project

Active-project resolution. Read prd.md frontmatter.

## Step 2 — Pre-flight checks

- The new version's folder must not already exist. If `.pm/<slug>/<new-version>/` exists, refuse and tell the user (offer to remove only if explicitly confirmed).
- Recommend (but don't require) that the previous version is released. If `prd.md` shows `active_version: v1` and no `v1/RELEASE.md` exists, warn: "v1 hasn't been released. Continue starting <new-version> anyway? (y/N)".

## Step 3 — Gather scope for the new version

Read `prd.md` and (if it exists) the previous version's `goals.md` and `RELEASE.md` "Known limitations" section to seed the conversation.

Adopt the **PM + dynamic Domain SME** persona pair (same as `/pm:prd`) and conduct a focused mini-interview specific to this version. Questions to cover:
1. **What's the headline goal of this version?**
2. **What's in scope?** (Pull from PRD goals not yet delivered, plus any new goals or carry-over limitations.)
3. **What's explicitly deferred to v(N+1)?**
4. **What changed in the world** since the prior version that affects this one? (Stakeholder shifts, new constraints, lessons learned from the prior release.)
5. **What's the acceptance bar for "this version is done"?**

Keep it shorter than `/pm:prd` — usually 1–2 rounds. The PRD already exists; you're just defining this version's cut.

## Step 4 — Scaffold the version folder

Create:
```
.pm/<slug>/<new-version>/
├── goals.md
├── research/      (empty — placeholder .gitkeep optional)
└── tasks/         (empty)
```

### `goals.md` content

```markdown
---
version: <new-version>
status: planning
created: <YYYY-MM-DD>
preceded_by: <prior-version-or-empty>
jira_epic: ""                 # set in Step 6.5 if Jira is enabled
---

# <new-version> — Goals

## What ships in <new-version>
<Concrete cut, referencing prd.md §N goals where applicable.>

## What's deferred from prior version
<Carry-overs and known limitations from previous RELEASE.md.>

## What's new in <new-version>
<Goals introduced for this version (new PRD goals or research-driven scope).>

## What's deferred to later versions
<Out of scope for this version, with target version or "TBD".>

## Acceptance bar
<Observable definition of "done" for this version.>

## Context from prior version
<One paragraph: what shipped, key lessons, what changed.>
```

## Step 4.5 — Carry forward architecture and test strategy (if any)

After scaffolding the folder, check whether the prior version has an `architecture.md`:
- `<prior-version>/architecture.md` exists → copy it to `<new-version>/architecture.md` and:
  - Update the copied file's frontmatter: `version: <new-version>`, `inherited_from: <prior-version>`, `status: drafted`.
  - Append a fresh Amendments entry recording the carry-forward:
    ```markdown
    ### <YYYY-MM-DD> — Inherited from <prior-version>
    **Why:** Starting <new-version> from the prior version's architecture as the baseline.
    **Change:** Copied verbatim. Edit this file or run `/pm:architect <slug>` (amend mode) to capture <new-version>-specific changes.
    ```
  - Tell the user: `Architecture inherited from <prior-version> → <new-version>/architecture.md.`
  - Ask: "Run `/pm:architect <slug>` now to amend for <new-version>, or skip and decide later?" — if yes, hand off; if no, the existing file stays as-is until the user runs it explicitly.
- `<prior-version>/architecture.md` missing → no copy; tell the user `No prior architecture to inherit. Consider running /pm:architect <slug> (and optionally /pm:test <slug>) before /pm:plan.`

Then check whether the prior version has a `testing.md`:
- `<prior-version>/testing.md` exists → copy it to `<new-version>/testing.md` and:
  - Update the copied file's frontmatter: `version: <new-version>`, `inherited_from: <prior-version>`, `status: drafted`.
  - Append a fresh Amendments entry recording the carry-forward:
    ```markdown
    ### <YYYY-MM-DD> — Inherited from <prior-version>
    **Why:** Starting <new-version> from the prior version's test strategy as the baseline.
    **Change:** Copied verbatim. Edit this file or run `/pm:test <slug>` (amend mode) to capture <new-version>-specific changes.
    ```
  - Tell the user: `Test strategy inherited from <prior-version> → <new-version>/testing.md.`
- `<prior-version>/testing.md` missing → no copy, no nag (testing.md is optional).

## Step 5 — Update PRD frontmatter

In `.pm/<slug>/prd.md`:
- `active_version: <new-version>`
- `status: active` (if it was `shipped` from the previous release closeout)

## Step 6 — Confirm with the user

Show the drafted `goals.md` to the user before writing. Apply edits.

## Step 6.5 — Create the Jira epic (optional, best-effort)

Run this block ONLY if all of these are true:

1. `.pm/<slug>/.jira.yml` exists.
2. `command -v acli` and `acli auth status` succeed. Otherwise print once: `Jira sync skipped — acli not available. Run /pm:jira-init for setup.` and skip.

If enabled, load `site`, `project_key`, and `epic_issue_type` from `.jira.yml`, then:

- Create a Jira epic via `acli` with:
  - **Summary** = `"<project title>" — <new-version>` (project title from prd.md frontmatter).
  - **Description** = the body of the drafted `goals.md` (everything below the frontmatter).
  - **Issue type** = `epic_issue_type`.
  - **Labels** = `["pm-<slug>", "<new-version>"]`.
- Capture the new epic key from `acli`'s output.
- Update `<new-version>/goals.md` frontmatter `jira_epic: <EPIC-KEY>`.

On any `acli` error, print ONE line: `Jira epic creation skipped (acli error: <message>). You can create the epic later via /pm:jira-init or directly in Jira, then set jira_epic in goals.md.` Continue — the version scaffold still succeeds without an epic.

## Step 7 — Hand off

Print:
- Paths created.
- The active version is now `<new-version>`.
- If Jira epic was created: `Jira epic: <EPIC-KEY>   https://<site>/browse/<EPIC-KEY>`.
- Next-step hint: `/pm:research <slug>` (recommended for any non-trivial version), or `/pm:plan <slug>` to go straight to tasks if the scope is well-understood.

## Output discipline
- This command does NOT touch the prior version's folder. Old goals, research, tasks, RELEASE.md stay frozen.
- If the user describes the new version's scope as basically a rewrite or pivot, surface that this might be better as a new project (`/pm:prd`) rather than a new version of the existing one.

---
description: Close out the active version of a project. Verifies all tasks are done, runs the final full-suite gate (/pm:gate), freezes the version folder, and writes RELEASE.md.
model: sonnet
argument-hint: <slug> [version]
---

# /pm:release — Close out a version

You are running the `/pm:release` command. The user is shipping the current version of the project.

## Inputs
Parse `$ARGUMENTS`:
- First token = slug (or empty → active-project resolution).
- Second token = version (optional, e.g. `v1`). If omitted, use `active_version` from prd.md frontmatter.

## Step 1 — Resolve project and version

Standard active-project resolution. Determine the target version.

## Step 2 — Gate check — all tasks must be done

Read every task file in `.pm/<slug>/<version>/tasks/`. Count by status.

**Refuse to release** if ANY task is `pending`, `in-progress`, `done-pending-verify`, or `rejected`. Print the offending tasks and tell the user:
```
Cannot release <version>. <N> task(s) not done:
  - 003 (rejected) — see Verifier notes
  - 007 (pending) — run /pm:execute
  - 009 (done-pending-verify) — run /pm:verify
Resolve these, then re-run /pm:release.
```

If `tasks/` is empty or doesn't exist, refuse — there's nothing to release.

If `RELEASE.md` already exists for this version, refuse — version already released. Suggest `/pm:version <slug> v<N+1>` to start the next one.

## Step 2.5 — Final full-suite gate

Status-done is necessary but not sufficient: per-task `/pm:verify` checks each task in isolation, so cross-cutting regressions (a change in a later task breaking an earlier one) can survive even when every task is `done`. Run the **final gate** before freezing the release:

Invoke `/pm:gate <slug> <version>` — it runs the project's full test suite and holistically re-checks the cumulative work against the goals + every task's acceptance criteria, writing `.pm/<slug>/<version>/gate-report.md`.

**Refuse to release** if the gate returns `verdict: FAIL`. Print the failures verbatim and stop:
```
Cannot release <version>. Final gate FAILED — see .pm/<slug>/<version>/gate-report.md:
  - [test] LocaleFormatTest#frDate — fr-FR renders MM/DD, expected DD/MM
  - [cross-cutting] 004↔002 — task 004's locale table overwrites task 002's keys
Fix these (or run /pm:auto <slug>, which re-gates and auto-remediates), then re-run /pm:release.
```

A `no-suite` caveat (the project has no detectable test suite) is NOT a hard failure — surface it as a warning and continue, since the gate still ran the holistic goal/criteria check. Only proceed to Step 3 once the gate is PASS.

## Step 3 — Gather release details

Ask the user (use AskUserQuestion where applicable):
1. **Release tag / version string** (e.g. "v1.0.0", "2026-Q2 launch", "internal beta"). Default: the version folder name.
2. **Deviations from goals.md?** Free-form — what shipped differently than originally scoped, and why.
3. **Links to PRs / commits / deployment evidence?** Free-form — paste URLs or commit SHAs.
4. **Known limitations carrying into next version?** These become seed material for v(N+1) planning.

## Step 4 — Write RELEASE.md

Create `.pm/<slug>/<version>/RELEASE.md`:

```markdown
---
version: <version folder name>
release_tag: <user-supplied tag>
released: <YYYY-MM-DD>
status: shipped
---

# <version> — Release notes

## What shipped
Summary derived from `<version>/goals.md` "What ships in <version>" minus any deviations.

## Tasks completed
- 001 — <title>
- 002 — <title>
- ...

## Deviations from original goals
<User-supplied — what shipped differently and why.>

## Evidence
- <links / commit SHAs from user>

## Known limitations
<Carrying into next version.>

## Research artifacts
- [Research index](research/_index.md) — <count> persona reports

## Amendments during this version
<List PRD Amendments dated within the version's active window, if any.>
```

## Step 5 — Update PRD frontmatter

In `.pm/<slug>/prd.md`, update the frontmatter:
- If this was the project's only version, set `status: shipped`.
- Otherwise leave `status` as-is (the next version will set it back to `active`).

In `.pm/<slug>/<version>/goals.md`, update frontmatter `status: shipped`.

## Step 6 — Optional: write a top-level changelog entry

If `.pm/<slug>/CHANGELOG.md` doesn't exist, ask the user if they want one created. If yes (or if it exists), prepend an entry:

```markdown
## <release_tag> — <YYYY-MM-DD>
<One-paragraph summary from RELEASE.md "What shipped".>
```

## Step 7 — Close the Jira epic (optional, best-effort)

Run this block ONLY if all of these are true:

1. `.pm/<slug>/.jira.yml` exists.
2. `command -v acli` and `acli auth status` succeed. Otherwise print once: `Jira sync skipped — acli not available. Run /pm:jira-init for setup.` and skip.
3. The released version's `goals.md` has a non-empty `jira_epic`. Otherwise skip silently.

If enabled, load `status_mapping` from `.jira.yml`, then:

- **Transition the epic** to `status_mapping.release_epic`.
- **Add a comment** on the epic with the release tag and the "What shipped" paragraph from RELEASE.md.

On any `acli` error, print ONE line: `Jira epic closure skipped (acli error: <message>). You can close the epic manually or use /pm:jira-sync later.` Continue — the release is complete on the pm side regardless.

## Step 8 — Hand off

Print:
- Path to RELEASE.md.
- Path to CHANGELOG.md (if created/updated).
- If epic was closed: `Jira epic <EPIC-KEY> → <status>.`
- Next-step hint: `/pm:version <slug> v<N+1>` to start the next milestone (if more work is expected), or "Project complete — set `status: archived` in prd.md when ready to file it away."

## Output discipline
- A release is a frozen artifact. Do not edit RELEASE.md after writing (the user can, but the command doesn't).
- Don't tag git, don't push, don't create GitHub releases unless the user asks explicitly. This command is about the PM artifact; release engineering is separate.

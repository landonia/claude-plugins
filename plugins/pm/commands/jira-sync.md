---
description: Reconcile Jira issue statuses with current pm task state. Useful after silent sync failures or first-run on existing projects.
argument-hint: [slug]
---

# /pm:jira-sync — Reconcile Jira with pm

You are running the `/pm:jira-sync` command. For every task with a linked Jira issue, push the current pm status to Jira via the configured mapping. Read-only on pm — Jira is the side that moves.

## Inputs
- Slug: `$ARGUMENTS` (active-project resolution if empty).

## Step 1 — Resolve project, version

Standard active-project resolution. Read `active_version` from prd.md frontmatter.

## Step 2 — Jira preflight

Required:
- `.pm/<slug>/.jira.yml` exists. If not, refuse with: "Jira not enabled for <slug>. Run /pm:jira-init first."
- `acli` installed and authenticated.

Load `.jira.yml`. Read `status_mapping`.

## Step 3 — Build the work list

List every task file in `<active_version>/tasks/` whose `jira_key` is non-empty. For each, capture: id, title, pm `status`, `jira_key`.

If the list is empty, tell the user "No linked tasks to sync." and stop.

## Step 4 — Compute target Jira status per task

Map pm status → target Jira status from `.jira.yml`:

| pm status                 | Jira target (from status_mapping)                                                |
|---------------------------|----------------------------------------------------------------------------------|
| `pending`                 | none — leave as-is (Jira default initial state should match)                     |
| `in-progress`             | `status_mapping.claim`                                                           |
| `done-pending-verify`     | `status_mapping.claim` (still in-progress — verify hasn't run yet)               |
| `done` (no `completed_at`)| `status_mapping.verify_accept`                                                   |
| `done` (with `completed_at`)| `status_mapping.complete`                                                      |
| `rejected`                | `status_mapping.verify_reject`                                                   |

## Step 5 — Read current Jira statuses

For each task, run `acli jira issue view <key>` to read the issue's current status. Compare to the target.

## Step 6 — Show the plan and confirm

Print a table:

```
Sync plan for <slug> <active_version>:
  ID   pm status              Jira (current → target)             Action
  001  done                   In Progress → In Review              transition
  002  in-progress            In Progress → In Progress            skip (already matches)
  003  rejected               Done → In Progress                   transition + comment
  ...
```

If everything matches, tell the user "All issues already in sync." and stop.

Otherwise, ask: **Apply <N> transitions? (y/N)**. Default no.

## Step 7 — Apply transitions

For each task needing a transition, call `acli` to perform the workflow transition. On failure, record the error and continue with the next task.

For `rejected` tasks, after the transition, also add a Jira comment with the latest `## Verifier notes — ... — REJECTED` section from the task body (mirrors `/pm:verify`'s on-reject behavior).

## Step 8 — Epic sync (if applicable)

Read `<active_version>/goals.md` frontmatter for `jira_epic`. If set:
- If the version's `goals.md` has `status: shipped`, target = `status_mapping.release_epic`.
- Otherwise, leave the epic as-is (epics transition explicitly on /pm:release).

If a transition is needed, apply the same way as task transitions. Refuse to transition an epic to "Done" if any child task is not `done` — surface the offending tasks.

## Step 9 — Hand off

Print:
```
Sync complete.
  Transitions applied: <N>
  Skipped (already in sync): <M>
  Failed: <F>
    001 — acli error: <message>
    ...

Next: /pm:status <slug>
```

## Output discipline

- Pm is the source of truth. NEVER edit pm task files in this command. Status flows pm → Jira only.
- A "transition" that's a no-op (current Jira status already matches target) should be silently skipped, not pushed.
- If `acli` reports a transition isn't available from the current status (workflow gates), surface the error per-task — don't try to chain transitions to reach the target.
- Don't add a "synced by /pm:jira-sync" comment on every issue — too noisy. Only the rejected-task verifier-notes comment is added.

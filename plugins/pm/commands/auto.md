---
description: Autonomously loop execute → verify in isolated subagents until no ready tasks remain. Stops on blockers, repeated rejections, or claimed-task stalls.
model: sonnet
argument-hint: [slug] [--max-retries N]
---

# /pm:auto — Autonomous execute → verify loop

You are running the `/pm:auto` command. You are the **orchestrator**. You do NOT implement or verify anything yourself — you pick tasks, dispatch isolated subagents, re-check state from disk, and decide whether to continue.

Each cycle: execute the next ready task in a fresh subagent, then verify it in another fresh subagent. ACCEPT → move to the next ready task. REJECT → re-execute the same task (the new executor picks up the `## Verifier notes` from disk). Repeat until no ready tasks remain or a stop condition fires.

This command covers ONLY the execute/verify phase. It never claims, completes, or releases.

## Inputs
Parse `$ARGUMENTS`:
- 0 args → active-project resolution.
- 1 arg slug → that project.
- `--max-retries N` (anywhere) → maximum rejections of the same task within this session. Default: 2. Note the arithmetic: default 2 means up to 3 executions of a task (initial attempt + re-attempts after rejections 1 and 2; the 2nd rejection ends the session). `--max-retries 0` = stop on the first rejection.

No task-id argument. To drive a specific task, run `/pm:execute <slug> <NNN>` and `/pm:verify <slug> <NNN>` supervised, then `/pm:auto <slug>` for the rest.

## Step 1 — Resolve project and version

Standard active-project resolution. Read `active_version` from prd.md frontmatter. Read the current git identity once (`git config user.name` + `user.email`) for claim checks.

## Step 2 — Pre-flight sweep

This is the ONLY interactive moment — after it, the loop runs unattended.

Inventory every task file's frontmatter in `.pm/<slug>/<active_version>/tasks/`:
- `done-pending-verify` tasks: nothing to do here — the loop drains them first (Step 3a).
- `in-progress` tasks need triage NOW, because the execute subagent cannot ask the user (it would take `/pm:execute`'s "redo? default no" and refuse):
  - `assignee` set to someone else → never touch; record in `skipped_claimed`.
  - Own/unassigned AND the task body has a `## Blocker` section → show the blocker; default to **skip** (a known blocker won't fix itself).
  - Own/unassigned, no blocker → AskUserQuestion: **resume** (treat as ready; the execute subagent prompt gets the pre-authorization line from Step 4) or **skip**.

Initialize session state:
- Rejection map: `task-id → rejections_this_session`, all starting at 0 — a task that enters the session already `rejected` gets a full fresh budget (its prior rejections happened under human supervision).
- Cycle counter and a derived hard cycle cap: `max_cycles = (tasks not yet done) × (max_retries + 1) + (count of done-pending-verify tasks) + 3`. This is anti-oscillation insurance, not a tunable — it should be unreachable.

If nothing is actionable at all (no ready, no done-pending-verify, no resumable in-progress), exit early with the appropriate `/pm:next`-style message (all done / blocked / no tasks).

## Step 3 — The loop

Repeat until a stop condition (Step 5):

**3a. Pick the phase.**
- Any task with status `done-pending-verify`? → **verify phase** on the lowest id. (This drains pre-existing backlog before new execution.)
- Else find the lowest-id **eligible** ready task → **execute phase**. Ready = status `pending` or `rejected` AND every id in `depends_on` has status `done` (same algorithm as `/pm:execute` Step 1), MINUS tasks whose `assignee` is set to someone other than the current git identity — record those in `skipped_claimed` and move to the next-lowest. NEVER pass `--force`.
- Else → stop (no eligible tasks).

**3b. Dispatch ONE Agent subagent** using the matching skeleton from Step 4. This is a serial pipeline — one subagent at a time. Parallel dispatch here is a bug.

**3c. Disk is truth.** After the subagent returns, re-read the task file's frontmatter `status` from disk. The subagent's report is advisory only — don't trust, verify. Then act:

| Phase   | Status on disk                          | Action                                                  |
|---------|------------------------------------------|---------------------------------------------------------|
| execute | `done-pending-verify`                    | proceed to verify phase next cycle                       |
| execute | `in-progress` + `## Blocker` present     | stop — print the `## Blocker` section verbatim           |
| execute | `in-progress`, no `## Blocker`           | anomaly — subagent died mid-work; stop, surface its report |
| execute | unchanged (`pending`/`rejected`)         | anomaly — subagent refused or failed; stop, surface      |
| verify  | `done`                                   | record completed; next cycle                             |
| verify  | `rejected`                               | increment rejection count; retry, or cap-stop if count = max_retries |
| verify  | unchanged (`done-pending-verify`)        | anomaly — verify subagent failed; stop, surface          |

**3d. Report.** Update counters and print one status line per cycle:

```
[cycle 3] task 004 <title> — execute ✓ → verify ✗ REJECTED (retry 1/2)
[cycle 4] task 004 <title> — execute ✓ → verify ✓ ACCEPTED
[cycle 5] task 006 <title> — execute ⊘ BLOCKED
```

Verify-only cycles (draining pre-existing backlog) render as `— verify ✓ ACCEPTED` with no execute segment.

## Step 4 — Subagent prompts

Both dispatched as `subagent_type: general-purpose`, one at a time. The Agent-level `model` param preserves the plugin's tiering regardless of how the subagent loads the command.

**Execute worker** (`model: sonnet`):

> You are an execute worker dispatched by `/pm:auto` for project `<slug>`.
>
> Invoke the Skill tool with skill `pm:execute` and args `<slug> <NNN>`, and follow that command fully. If the Skill tool is unavailable or `pm:execute` is not in your available skills, instead read `${CLAUDE_PLUGIN_ROOT}/commands/execute.md` and follow its contents as your instructions, treating `$ARGUMENTS` as `<slug> <NNN>`.
>
> Rules: work ONLY task `<NNN>` — never auto-pick another. Never pass `--force`. Never commit or push. Do not run `pm:verify` or any other pm command. You cannot ask the user questions: where `pm:execute` would ask one, take the safe default — and if you cannot complete the task, follow its blocker protocol exactly (leave status `in-progress`, write a `## Blocker` section with specifics) rather than improvising, lowering the bar, or flipping the status anyway.
>
> *(Include ONLY when pre-flight authorized a resume:)* The user has already approved redoing this `in-progress` task — proceed past the redo confirmation.
>
> When finished, report back ONLY: the task's final frontmatter `status` as read from the task file, a one-line summary of what you did, and the `## Blocker` text verbatim if you wrote one. No diffs, no implementation detail — everything the verifier needs is on disk.

**Verify worker** (`model: opus`):

> You are an independent verifier dispatched by `/pm:auto` for project `<slug>`.
>
> Invoke the Skill tool with skill `pm:verify` and args `<slug> <NNN>`, and follow that command fully. If the Skill tool is unavailable or `pm:verify` is not in your available skills, instead read `${CLAUDE_PLUGIN_ROOT}/commands/verify.md` and follow its contents as your instructions, treating `$ARGUMENTS` as `<slug> <NNN>`.
>
> Rules: verify ONLY task `<NNN>`. You did not write this code; judge it cold. Never modify implementation files — only the task file, per `pm:verify`. Never commit or push. If borderline, REJECT with specific notes.
>
> When finished, report back ONLY: the verdict (ACCEPT/REJECT), the task's final frontmatter `status` as read from the task file, and a one-line summary. No verification reasoning — your notes live in the task file.

Never paste task-file, PRD, or code content into a subagent prompt beyond slug + task id — the subagent reads everything from disk itself. Whatever the subagent reports, the orchestrator re-reads status from disk (Step 3c).

## Step 5 — Stop conditions

Stop the loop and run Step 6 when any of these fires:

- **All done** — no eligible ready and no done-pending-verify tasks remain, and every task is `done`.
- **Retry cap** — a task's rejection count reaches `max_retries`. Print its latest `## Verifier notes — <date> — REJECTED` section verbatim. A repeatedly-failing task usually signals a planning or criteria problem; its dependents are blocked anyway. Hint: `/pm:execute <slug> <NNN>` for a supervised retry.
- **Blocker** — execute subagent left `in-progress` + `## Blocker`. Print the blocker verbatim. Hint: resolve it, then re-run `/pm:auto <slug>` — pre-flight will offer to resume the task.
- **No eligible tasks** — ready tasks exist but all are claimed by others, or pending tasks are blocked behind skipped/claimed ones. Report this as "no eligible tasks", NOT "all done" — list who holds what.
- **Cycle cap** — `max_cycles` reached. This almost certainly indicates a bug worth reporting.
- **Anomaly** — any anomaly row from the Step 3c table.

## Step 6 — Final summary

Always printed, whatever the stop reason:

```
/pm:auto finished — <reason: all tasks done | retry cap hit on 004 | blocker on 006 | no eligible tasks | cycle cap hit>
Cycles run:        7
Completed:         003, 004, 005
Rejection-capped:  —  (or: 004 — 2 rejections, see ## Verifier notes)
Skipped (claimed): 002 (Alice <a@example.com>)
Blocked:           —  (or: 006 — see ## Blocker)
Next: /pm:release <slug>   (only when every task in the active version is done;
      otherwise a stop-reason-appropriate hint: /pm:execute <slug> <NNN>, /pm:status <slug>, …)
```

## Context isolation guarantees

This command exists to keep state in files, not in context:

- Every phase — each execute, each verify, each retry — is a **brand-new subagent with a fresh context**. A retry of a rejected task has no memory of the prior attempt; it learns what went wrong solely from the `## Verifier notes` on disk. That is the plugin's existing contract ("rejection notes MUST be specific enough that a NEW executor with no memory of the prior attempt could pick up and finish").
- The verifier-independence guarantee survives automation: the verify subagent never shares context with the executor that produced the work.
- Subagent reports are brief (status + one line + blocker text if any). The orchestrator's context holds only counters and per-cycle status lines — no diffs, no implementation detail, no verification reasoning. If a subagent's report is long, ignore the excess; the files are the record.

## Output discipline
- Never pass `--force` to anything. Never claim, complete, or release.
- Never edit task files yourself — subagents own all status flips. You only read.
- Disk is truth: re-read frontmatter after every subagent; reports are advisory.
- Serial dispatch only — parallel Agent calls here are a bug.
- Don't commit/push, and don't let subagents commit/push.
- Surface failures verbatim (`## Blocker`, `## Verifier notes`) — don't paraphrase them away.

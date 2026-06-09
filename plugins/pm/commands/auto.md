---
description: Autonomously loop execute → verify in isolated subagents until no ready tasks remain. Stops on blockers, repeated rejections, or claimed-task stalls.
model: sonnet
argument-hint: [slug] [--max-retries N]
---

# /pm:auto — Autonomous execute → verify loop

You are running the `/pm:auto` command. You are the **orchestrator**. You do NOT implement or verify anything yourself — you pick tasks, dispatch isolated subagents, re-check state from disk, and decide whether to continue.

Each cycle: execute the next ready task in a fresh subagent, then verify it in another fresh subagent. ACCEPT → move to the next ready task. REJECT → re-execute the same task (the new executor picks up the `## Verifier notes` from disk). Repeat until no ready tasks remain or a stop condition fires.

The loop itself runs as a **deterministic Workflow** (Step 3): a real code `while` loop drives the cycles, so it cannot spuriously stop between tasks the way a prose loop can. Continuation is guaranteed by code, not by model disposition. If the Workflow tool is unavailable in this environment, fall back to the hardened in-context loop at the end of this file.

This command covers ONLY the execute/verify phase. It never claims, completes, or releases.

## Inputs
Parse `$ARGUMENTS`:
- 0 args → active-project resolution.
- 1 arg slug → that project.
- `--max-retries N` (anywhere) → maximum rejections of the same task within this session. Default: 2. Note the arithmetic: default 2 means up to 3 executions of a task (initial attempt + re-attempts after rejections 1 and 2; the 2nd rejection ends the session). `--max-retries 0` = stop on the first rejection.

You do NOT extract `N` yourself for the Workflow — pass `$ARGUMENTS` verbatim as `rawArgs` (Step 3.1) and the deterministic script parses the flag in code, so its effect never depends on model parsing. You still read the slug from `$ARGUMENTS` for project resolution.

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

Record the pre-flight decisions for the loop:
- `resume_authorized`: list of task ids the user approved resuming.
- `skipped_claimed`: list of `{id, owner}` for tasks held by others.

If nothing is actionable at all (no ready, no done-pending-verify, no resumable in-progress), exit early with the appropriate `/pm:next`-style message (all done / blocked / no tasks).

## Step 3 — Run the loop (Workflow)

The loop is a deterministic Workflow. By instructing you to call the Workflow tool, this command is your explicit opt-in to use it — call it directly; do not ask the user first.

**3.1 — Build the inputs.** Compute the absolute tasks directory and resolve the plugin command paths (`${CLAUDE_PLUGIN_ROOT}` is expanded here, in the command — the Workflow script cannot expand env vars itself). Assemble the `args` object:

```
args = {
  slug:             "<slug>",
  version:          "<active_version>",
  tasksDir:         "<abs path to .pm/<slug>/<active_version>/tasks>",
  executeCmdPath:   "${CLAUDE_PLUGIN_ROOT}/commands/execute.md",
  verifyCmdPath:    "${CLAUDE_PLUGIN_ROOT}/commands/verify.md",
  rawArgs:          "<the verbatim $ARGUMENTS string, e.g. 'myproj --max-retries 5'>",
  gitEmail:         "<git config user.email>",
  resumeAuthorized: [<task ids approved for resume in Step 2>],
  skippedClaimed:   [<{id, owner} recorded in Step 2>],
}
```

`maxRetries` is NOT in this object — the script parses it from `rawArgs` in code (Step 3 script), so the `--max-retries` flag takes effect deterministically rather than depending on the orchestrator extracting the number. `slug` is also recovered from `tasksDir` in the script if you omit it, so the dispatched worker prompts can't say `'undefined'` — but still populate it here.

**3.2 — Dispatch the loop.** Call the **Workflow tool** with the `args` above and the `script` below verbatim. The Workflow runs in the background; per-cycle progress is visible live via `/workflows`, and you are re-invoked when it finishes. When it returns its result object, print the Step 6 summary from it.

**3.3 — Fallback.** If the Workflow tool is not available in this environment, do NOT improvise — follow the **Fallback loop** section at the end of this file instead.

The script (pass exactly as `script`):

```js
export const meta = {
  name: 'pm-auto-loop',
  description: 'Autonomous execute -> verify loop for a pm project until done or blocked',
  phases: [{ title: 'Loop' }],
}

// --- Schemas (the script has no filesystem access; every disk read is an agent) ---
const SNAPSHOT = {
  type: 'object',
  required: ['tasks'],
  properties: {
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'status', 'depends_on', 'assignee', 'hasBlocker', 'hasVerifierNotes'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          status: { type: 'string' },
          depends_on: { type: 'array', items: { type: 'string' } },
          assignee: { type: ['string', 'null'] },
          hasBlocker: { type: 'boolean' },
          blockerText: { type: ['string', 'null'] },
          hasVerifierNotes: { type: 'boolean' },
          verifierNotesText: { type: ['string', 'null'] },
        },
      },
    },
  },
}
const WORKER = {
  type: 'object',
  required: ['status', 'summary'],
  properties: {
    status: { type: 'string' },
    summary: { type: 'string' },
    blockerText: { type: ['string', 'null'] },
  },
}
const VERDICT = {
  type: 'object',
  required: ['verdict', 'status', 'summary'],
  properties: {
    verdict: { type: 'string' },
    status: { type: 'string' },
    summary: { type: 'string' },
  },
}

// --- Resolve slug deterministically: prefer the orchestrator's value, else
//     recover it from tasksDir (.pm/<slug>/<version>/tasks) so worker prompts
//     never say 'undefined' when the model omits args.slug.
const _td = String(args.tasksDir || '').match(/\.pm\/([^/]+)\/[^/]+\/tasks\/?$/)
const slug = args.slug || (_td && _td[1]) || 'unknown'

// --- Worker prompts (mirror Step 4; only slug + id cross the boundary) ---
function executePrompt(id, resumeLine) {
  return [
    `You are an execute worker dispatched by /pm:auto for project '${slug}'.`,
    ``,
    `Invoke the Skill tool with skill 'pm:execute' and args '${slug} ${id}', and follow that command fully. If the Skill tool is unavailable or 'pm:execute' is not in your available skills, instead Read the file '${args.executeCmdPath}' and follow its contents as your instructions, treating $ARGUMENTS as '${slug} ${id}'.`,
    ``,
    `Rules: work ONLY task ${id} — never auto-pick another. Never pass --force. Never commit or push. Do not run pm:verify or any other pm command. You cannot ask the user questions: where pm:execute would ask one, take the safe default — and if you cannot complete the task, follow its blocker protocol exactly (leave status 'in-progress', write a '## Blocker' section with specifics) rather than improvising, lowering the bar, or flipping the status anyway.${resumeLine}`,
    ``,
    `When finished, report back ONLY: the task's final frontmatter 'status' as read from the task file, a one-line summary, and the '## Blocker' text verbatim if you wrote one. Everything the verifier needs is on disk.`,
  ].join('\n')
}
function verifyPrompt(id) {
  return [
    `You are an independent verifier dispatched by /pm:auto for project '${slug}'.`,
    ``,
    `Invoke the Skill tool with skill 'pm:verify' and args '${slug} ${id}', and follow that command fully. If the Skill tool is unavailable or 'pm:verify' is not in your available skills, instead Read the file '${args.verifyCmdPath}' and follow its contents as your instructions, treating $ARGUMENTS as '${slug} ${id}'.`,
    ``,
    `Rules: verify ONLY task ${id}. You did not write this code; judge it cold. Never modify implementation files — only the task file, per pm:verify. Never commit or push. If borderline, REJECT with specific notes.`,
    ``,
    `When finished, report back ONLY: the verdict (ACCEPT/REJECT), the task's final frontmatter 'status' as read from the task file, and a one-line summary.`,
  ].join('\n')
}

const snapshotPrompt =
  `You are a read-only status reader for /pm:auto, project '${slug}'.\n` +
  `Read EVERY '*.md' task file in this directory:\n  ${args.tasksDir}\n` +
  `For each task return one object with:\n` +
  `- id: the 3-digit task id (frontmatter 'id', else the leading number of the filename, zero-padded to 3)\n` +
  `- title: frontmatter 'title' (or the first heading)\n` +
  `- status: frontmatter 'status' verbatim\n` +
  `- depends_on: frontmatter 'depends_on' as an array of 3-digit id strings (empty array if none)\n` +
  `- assignee: frontmatter 'assignee' verbatim, or null if absent/empty\n` +
  `- hasBlocker / blockerText: whether the body has a '## Blocker' section, and its full text (else false / null)\n` +
  `- hasVerifierNotes / verifierNotesText: whether the body has a '## Verifier notes' section, and the text of the MOST RECENT one (else false / null)\n` +
  `READ ONLY — do not modify any file. Return every task.`

// --- Loop state (held in code, the source of all flow decisions) ---
const _mr = String(args.rawArgs || '').match(/--max-retries[=\s]+(\d+)/)
const maxRetries = _mr ? parseInt(_mr[1], 10)
  : (Number.isInteger(args.maxRetries) ? args.maxRetries : 2)
log(`max-retries = ${maxRetries}${_mr ? ' (from --max-retries)' : ' (default)'}`)
const me = String(args.gitEmail || '').toLowerCase()
const rejections = {}                 // id -> rejections this session
const completed = []
const skippedClaimed = Array.isArray(args.skippedClaimed) ? args.skippedClaimed.slice() : []
const resumeAuthorized = Array.isArray(args.resumeAuthorized) ? args.resumeAuthorized : []
let cycle = 0
let last = null                       // {phase:'execute'|'verify', id}
let maxCycles = null
const out = { reason: null, completed, rejectionCapped: null, blocked: null, skippedClaimed, cycles: 0 }

const heldByOther = (a) => !!a && !String(a).toLowerCase().includes(me)
const ready = (t, byId) =>
  (t.status === 'pending' || t.status === 'rejected') &&
  (t.depends_on || []).every(d => byId[d] && byId[d].status === 'done')

while (true) {
  // (1) Disk is truth — a fresh, independent snapshot every iteration.
  const snap = await agent(snapshotPrompt, { schema: SNAPSHOT, model: 'haiku', label: 'snapshot', phase: 'Loop' })
  const tasks = (snap && snap.tasks) || []
  const byId = {}
  for (const t of tasks) byId[t.id] = t

  if (maxCycles === null) {
    const notDone = tasks.filter(t => t.status !== 'done').length
    const dpv0 = tasks.filter(t => t.status === 'done-pending-verify').length
    maxCycles = notDone * (maxRetries + 1) + dpv0 + 3   // anti-oscillation insurance; should be unreachable
  }
  if (cycle++ > maxCycles) { out.reason = 'cycle cap hit'; break }

  // (2) Reconcile the PREVIOUS dispatch against fresh disk state (never trust the worker's report).
  if (last) {
    const t = byId[last.id]
    if (last.phase === 'execute') {
      if (!t || t.status !== 'done-pending-verify') {
        if (t && t.status === 'in-progress' && t.hasBlocker) {
          out.reason = 'blocker'; out.blocked = { id: last.id, text: t.blockerText }
          log(`[cycle ${cycle}] task ${last.id} — execute ⊘ BLOCKED`); break
        }
        out.reason = 'anomaly'
        out.blocked = { id: last.id, text: (t && t.blockerText) || `execute left status '${t ? t.status : 'missing'}'` }
        log(`[cycle ${cycle}] task ${last.id} — execute ✗ ANOMALY (${t ? t.status : 'missing'})`); break
      }
    } else { // verify
      if (t && t.status === 'done') {
        if (!completed.includes(last.id)) completed.push(last.id)
        log(`[cycle ${cycle}] task ${last.id} ${t.title} — verify ✓ ACCEPTED`)
      } else if (t && t.status === 'rejected') {
        rejections[last.id] = (rejections[last.id] || 0) + 1
        log(`[cycle ${cycle}] task ${last.id} ${t.title} — verify ✗ REJECTED (retry ${rejections[last.id]}/${maxRetries})`)
        if (rejections[last.id] >= maxRetries) {
          out.reason = 'retry cap hit'
          out.rejectionCapped = { id: last.id, rejections: rejections[last.id], notes: t.verifierNotesText }
          break
        }
      } else {
        out.reason = 'anomaly'
        out.blocked = { id: last.id, text: `verify left status '${t ? t.status : 'missing'}'` }
        log(`[cycle ${cycle}] task ${last.id} — verify ✗ ANOMALY (${t ? t.status : 'missing'})`); break
      }
    }
  }

  // (3) Pick the phase (Step 3a) in code: drain done-pending-verify first, else lowest eligible ready.
  const byIdAsc = (a, b) => a.id.localeCompare(b.id)
  const dpv = tasks.filter(t => t.status === 'done-pending-verify').sort(byIdAsc)
  let phase = null, pick = null
  if (dpv.length) { phase = 'verify'; pick = dpv[0] }
  else {
    const eligible = tasks.filter(t => ready(t, byId)).filter(t => {
      if (heldByOther(t.assignee)) {
        if (!skippedClaimed.find(s => s.id === t.id)) skippedClaimed.push({ id: t.id, owner: t.assignee })
        return false
      }
      return true
    }).sort(byIdAsc)
    if (eligible.length) { phase = 'execute'; pick = eligible[0] }
  }

  if (!pick) {
    out.reason = (tasks.length > 0 && tasks.every(t => t.status === 'done')) ? 'all tasks done' : 'no eligible tasks'
    break
  }

  // (4) Dispatch ONE worker, serially. Continuation is the loop; the model never decides to stop here.
  if (phase === 'execute') {
    const resumeLine = resumeAuthorized.includes(pick.id)
      ? `\n\nThe user has already approved redoing this in-progress task — proceed past the redo confirmation.` : ''
    await agent(executePrompt(pick.id, resumeLine), { schema: WORKER, model: 'sonnet', label: `execute:${pick.id}`, phase: 'Loop' })
  } else {
    await agent(verifyPrompt(pick.id), { schema: VERDICT, model: 'opus', label: `verify:${pick.id}`, phase: 'Loop' })
  }
  last = { phase, id: pick.id }
}

out.cycles = cycle
out.skippedClaimed = skippedClaimed
return out
```

When the Workflow returns, go to Step 6 and print the summary from the returned object (`reason`, `completed`, `rejectionCapped`, `blocked`, `skippedClaimed`, `cycles`).

## Step 4 — Subagent worker prompts

These are the prompts the loop dispatches (embedded in the Step 3 script as `executePrompt` / `verifyPrompt`, and used verbatim by the Fallback loop). Keep the two copies in sync. Both run as `subagent_type: general-purpose`, one at a time; the per-agent `model` preserves the plugin's tiering.

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

Never paste task-file, PRD, or code content into a subagent prompt beyond slug + task id — the subagent reads everything from disk itself. Whatever the subagent reports, the orchestrator re-reads status from disk via the next snapshot.

## Step 5 — Stop conditions

The loop computes these in code (Step 3 script) from each fresh snapshot. It stops and runs Step 6 when any fires:

- **All done** — no eligible ready and no done-pending-verify tasks remain, and every task is `done`. (`reason: 'all tasks done'`)
- **Retry cap** — a task's rejection count reaches `max_retries`. Print its latest `## Verifier notes — <date> — REJECTED` section verbatim (carried as `rejectionCapped.notes`). A repeatedly-failing task usually signals a planning or criteria problem; its dependents are blocked anyway. Hint: `/pm:execute <slug> <NNN>` for a supervised retry.
- **Blocker** — execute worker left `in-progress` + `## Blocker`. Print the blocker verbatim (`blocked.text`). Hint: resolve it, then re-run `/pm:auto <slug>` — pre-flight will offer to resume the task.
- **No eligible tasks** — ready tasks exist but all are claimed by others, or pending tasks are blocked behind skipped/claimed ones. Report as "no eligible tasks", NOT "all done" — list who holds what (`skippedClaimed`).
- **Cycle cap** — `max_cycles` reached. This almost certainly indicates a bug worth reporting.
- **Anomaly** — a worker died mid-work, refused, or failed (disk status didn't advance as expected). Surface the worker's state.

## Step 6 — Final summary

Always printed by you (the orchestrator) when the Workflow returns, whatever the stop reason:

```
/pm:auto finished — <reason: all tasks done | retry cap hit on 004 | blocker on 006 | no eligible tasks | cycle cap hit | anomaly>
Cycles run:        7
Completed:         003, 004, 005
Rejection-capped:  —  (or: 004 — 2 rejections, see ## Verifier notes)
Skipped (claimed): 002 (Alice <a@example.com>)
Blocked:           —  (or: 006 — see ## Blocker)
Next: /pm:release <slug>   (only when every task in the active version is done;
      otherwise a stop-reason-appropriate hint: /pm:execute <slug> <NNN>, /pm:status <slug>, …)
```

## Fallback loop (only when the Workflow tool is unavailable)

Run the loop yourself, in this context. **Continuation contract — read this first:** after EVERY subagent tool result your turn is **not** over. Your immediate next action is exactly one of: (a) dispatch the next subagent, or (b) print the Step 6 summary because a Step 5 stop condition fired. Ending your turn in any other situation — eligible tasks remaining, no stop condition met — is a defect, not a stopping point. Do not narrate, summarize progress, or yield between cycles; just continue.

Initialize session state: a rejection map (`task-id → rejections_this_session`, all 0) and a cycle cap `max_cycles = (tasks not yet done) × (max_retries + 1) + (count of done-pending-verify tasks) + 3`.

Repeat until a Step 5 stop condition fires:

**3a. Pick the phase.** Any `done-pending-verify` task → **verify phase** on the lowest id (drains pre-existing backlog first). Else the lowest-id **eligible** ready task → **execute phase**. Ready = status `pending`/`rejected` AND every `depends_on` id is `done`, MINUS tasks whose `assignee` is someone other than the current git identity (record those in `skipped_claimed`). NEVER pass `--force`. Else → stop (no eligible tasks).

**3b. Dispatch ONE Agent subagent** (the matching Step 4 prompt). Serial — one at a time; parallel dispatch here is a bug.

**3c. Disk is truth.** Re-read the task file's frontmatter `status` from disk; the subagent's report is advisory. Then act:

| Phase   | Status on disk                       | Action                                                          |
|---------|--------------------------------------|-----------------------------------------------------------------|
| execute | `done-pending-verify`                | proceed to verify phase next cycle                              |
| execute | `in-progress` + `## Blocker`         | stop — print the `## Blocker` section verbatim                  |
| execute | `in-progress`, no `## Blocker`       | anomaly — subagent died mid-work; stop, surface its report     |
| execute | unchanged (`pending`/`rejected`)     | anomaly — subagent refused or failed; stop, surface            |
| verify  | `done`                               | record completed; next cycle                                   |
| verify  | `rejected`                           | increment rejection count; retry, or cap-stop if count = max_retries |
| verify  | unchanged (`done-pending-verify`)    | anomaly — verify subagent failed; stop, surface                |

**3d. Report** one status line per cycle, then immediately continue per the continuation contract:

```
[cycle 3] task 004 <title> — execute ✓ → verify ✗ REJECTED (retry 1/2)
[cycle 4] task 004 <title> — execute ✓ → verify ✓ ACCEPTED
[cycle 5] task 006 <title> — execute ⊘ BLOCKED
```

When a stop condition fires, print the Step 6 summary.

## Context isolation guarantees

This command exists to keep state in files, not in context:

- Every phase — each execute, each verify, each retry — is a **brand-new subagent with a fresh context**. A retry of a rejected task has no memory of the prior attempt; it learns what went wrong solely from the `## Verifier notes` on disk. That is the plugin's existing contract ("rejection notes MUST be specific enough that a NEW executor with no memory of the prior attempt could pick up and finish").
- The verifier-independence guarantee survives automation: the verify subagent never shares context with the executor that produced the work.
- The control loop holds only counters and per-cycle status lines — no diffs, no implementation detail, no verification reasoning. Even the worker's structured return is advisory; flow decisions come only from the fresh on-disk snapshot.

## Output discipline
- Never pass `--force` to anything. Never claim, complete, or release.
- Never edit task files yourself — subagents own all status flips. The loop only reads (via the snapshot agent).
- Disk is truth: re-read frontmatter every iteration; worker reports are advisory.
- Serial dispatch only — concurrent worker calls here are a bug.
- Don't commit/push, and don't let subagents commit/push.
- Surface failures verbatim (`## Blocker`, `## Verifier notes`) — don't paraphrase them away.

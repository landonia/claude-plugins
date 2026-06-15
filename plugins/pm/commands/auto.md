---
description: Autonomously loop execute → verify in isolated subagents until no ready tasks remain. Stops on blockers, repeated rejections, or claimed-task stalls.
model: sonnet
argument-hint: [slug] [--max-retries N] [--parallel [N]]
---

# /pm:auto — Autonomous execute → verify loop

You are running the `/pm:auto` command. You are the **orchestrator**. You do NOT implement or verify anything yourself — you pick tasks, dispatch isolated subagents, re-check state from disk, and decide whether to continue.

Each cycle: execute the next ready task in a fresh subagent, then verify it in another fresh subagent. ACCEPT → move to the next ready task. REJECT → re-execute the same task (the new executor picks up the `## Verifier notes` from disk). Repeat until no ready tasks remain or a stop condition fires.

The loop itself runs as a **deterministic Workflow** (Step 3): a real code `while` loop drives the cycles, so it cannot spuriously stop between tasks the way a prose loop can. Continuation is guaranteed by code, not by model disposition. If the Workflow tool is unavailable in this environment, fall back to the hardened in-context loop at the end of this file.

By default this command runs **sequentially** — one execute/verify worker at a time against the shared working tree. With the opt-in `--parallel [N]` flag (Step 3-P) it instead runs up to N task pipelines concurrently, each in its own git worktree, merging accepted work back into your branch as it lands. Parallel mode trades the serial "workers never commit" contract for real concurrency and requires the Workflow tool; without it, `--parallel` degrades to the sequential fallback. **Sequential is the default; nothing below the `--parallel` sections changes unless the flag is present.**

This command covers ONLY the execute/verify phase. It never claims, completes, or releases. (In `--parallel` mode it does commit accepted work to per-task branches and merge them into your current branch — see Step 3-P — but it still never pushes, opens PRs, or releases.)

## Inputs
Parse `$ARGUMENTS`:
- 0 args → active-project resolution.
- 1 arg slug → that project.
- `--max-retries N` (anywhere) → maximum rejections of the same task within this session. Default: 2. Note the arithmetic: default 2 means up to 3 executions of a task (initial attempt + re-attempts after rejections 1 and 2; the 2nd rejection ends the session). `--max-retries 0` = stop on the first rejection.
- `--parallel [N]` (anywhere) → opt into concurrent task execution (Step 3-P). `N` is the maximum number of task pipelines in flight at once; bare `--parallel` defaults to **3**. Effective concurrency is also bounded by the Workflow tool's cap (~10) and by the dependency graph's width. `--parallel 0` and `--parallel 1` mean "sequential" → use the serial Step 3 script. Absent the flag, the command is sequential.

You do NOT extract `N` (for either flag) yourself for the Workflow — pass `$ARGUMENTS` verbatim as `rawArgs` (Step 3.1) and the deterministic script parses the flags in code, so their effect never depends on model parsing. You DO detect the **presence** of `--parallel` (a single boolean) to decide which script to dispatch in Step 3, and you read the slug from `$ARGUMENTS` for project resolution.

No task-id argument. To drive a specific task, run `/pm:execute <slug> <NNN>` and `/pm:verify <slug> <NNN>` supervised, then `/pm:auto <slug>` for the rest.

## Step 1 — Resolve project and version

Standard active-project resolution. Read `active_version` from prd.md frontmatter. Read the current git identity once (`git config user.name` + `user.email`) for claim checks. When `--parallel` is present, also read the current branch once (`git rev-parse --abbrev-ref HEAD`) — it becomes the **integration branch** that accepted work merges into (passed as `integrationBranch` in Step 3.1).

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

**Parallel-mode pre-flight (only when `--parallel` is present).** Before dispatching the Step 3-P script, do this once, interactively:
- **Cleanliness gate (do this FIRST — it prevents the file-loss failure mode).** Each execute/verify worker runs in a real, separate git worktree that the harness builds from a *commit*, so it can only see work that is already committed on `integrationBranch` — uncommitted or untracked files (notably the `.pm/<slug>/` task files themselves) are invisible to workers and can be silently clobbered. Run `git status --porcelain`. If it is non-empty:
  - Explain the above plainly, then `AskUserQuestion`: **commit the `.pm/<slug>/` task files now and proceed**, or **abort** (default: abort — do NOT proceed on a dirty tree).
  - If non-`.pm` changes are also present, surface them by name and default to **abort** — never auto-commit unrelated work.
  - If the user chooses to commit, stage only the project's task files and commit, e.g. `git add .pm/<slug>/ && git commit -m "pm <slug>: snapshot tasks before --parallel"`, then continue. If they abort, stop here and tell them to commit/stash first.
- State the contract change plainly: in `--parallel` mode each task runs in its own git worktree, the execute worker **commits** its work to a per-task branch (`pm/<slug>/<NNN>-<task-slug>`), and accepted work is **merged into the current branch** (`integrationBranch`). This relaxes the serial-mode "workers never commit" rule, and means this run will leave commits on your branch.
- If `integrationBranch` is the repository's default branch (`main` or `master`), warn loudly and AskUserQuestion whether to proceed — merging task commits directly onto `main` is usually not what you want; suggest creating/switching to a feature branch first. Default to **not** proceeding.
- The shared-tree concerns above (claimed in-progress tasks, blockers) still apply identically; the per-task worktrees only change where execution happens, not the pre-flight triage.
- If any task is already `done-pending-verify` (e.g. left by an interrupted serial run), note that parallel mode cannot verify pre-existing **uncommitted** work in isolation — its verifiers read committed task branches. Recommend draining those first with a sequential `/pm:auto <slug>` (no flag), then re-running with `--parallel`. Parallel mode runs the `pending`/`rejected`/authorized-resume frontier.

## Step 3 — Run the loop (Workflow)

The loop is a deterministic Workflow. By instructing you to call the Workflow tool, this command is your explicit opt-in to use it — call it directly; do not ask the user first.

**Which script.** If `--parallel` was present in `$ARGUMENTS` (and was not `--parallel 0` / `--parallel 1`), dispatch the **Step 3-P parallel script** instead of the serial script below; build the same `args` object plus `integrationBranch` (Step 3.1). Otherwise — the default — dispatch the serial script in this section unchanged. Everything in Step 3.1–3.3 (build inputs, pass `args` as a real JSON object, fall back when the Workflow tool is missing) applies to both scripts; only the `script` body differs.

**3.1 — Build the inputs.** Compute the absolute tasks directory and resolve the plugin command paths (`${CLAUDE_PLUGIN_ROOT}` is expanded here, in the command — the Workflow script cannot expand env vars itself). Assemble the `args` object:

```
args = {
  slug:             "<slug>",
  version:          "<active_version>",
  tasksDir:         "<abs path to .pm/<slug>/<active_version>/tasks>",
  tasksDirRel:      "<repo-relative tasks dir, e.g. '.pm/<slug>/<active_version>/tasks' — used by the worktree-isolated execute/verify workers; optional, the script derives it from tasksDir if omitted>",
  executeCmdPath:   "${CLAUDE_PLUGIN_ROOT}/commands/execute.md",
  verifyCmdPath:    "${CLAUDE_PLUGIN_ROOT}/commands/verify.md",
  rawArgs:          "<the verbatim $ARGUMENTS string, e.g. 'myproj --max-retries 5'>",
  gitEmail:         "<git config user.email>",
  resumeAuthorized: [<task ids approved for resume in Step 2>],
  skippedClaimed:   [<{id, owner} recorded in Step 2>],
  integrationBranch:"<git rev-parse --abbrev-ref HEAD — ONLY needed for the Step 3-P parallel script; omit/empty for serial>",
}
```

`maxRetries` is NOT in this object — the script parses it from `rawArgs` in code (Step 3 script), so the `--max-retries` flag takes effect deterministically rather than depending on the orchestrator extracting the number. `slug` is also recovered from `tasksDir` in the script if you omit it, so the dispatched worker prompts can't say `'undefined'` — but still populate it here.

**3.2 — Dispatch the loop.** Call the **Workflow tool** with the `args` above and the `script` below verbatim. **Pass `args` as an actual JSON object value, NOT a JSON-encoded string** — if you stringify it, every `args.X` read inside the script is `undefined` and workers get dispatched with project `'unknown'` and path `'undefined'`. (The script also defensively `JSON.parse`s a stringified `args` as a backstop, but pass an object regardless.) The Workflow runs in the background; per-cycle progress is visible live via `/workflows`, and you are re-invoked when it finishes. When it returns its result object, print the Step 6 summary from it.

**3.3 — Fallback.** If the Workflow tool is not available in this environment, do NOT improvise — follow the **Fallback loop** section at the end of this file instead.

The script (pass exactly as `script`):

```js
export const meta = {
  name: 'pm-auto-loop',
  description: 'Autonomous execute -> verify loop for a pm project until done or blocked',
  phases: [{ title: 'Loop' }],
}

// --- Normalize args: some orchestrators serialize the args object to a JSON
//     string before passing it to the Workflow tool. When that happens, every
//     args.X read is undefined (string has no such property) and workers get
//     dispatched with project 'unknown' / path 'undefined'. Parse it back so
//     the loop is robust to that, regardless of how the model fills the input.
if (typeof args === 'string') { try { args = JSON.parse(args) } catch (e) { /* leave as-is; guard below reports */ } }

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
//     recover it from rawArgs (first non-flag token the user typed) or from
//     tasksDir (first path segment after '.pm/', any depth) so worker prompts
//     never say 'unknown' when the model omits args.slug.
const _td = String(args.tasksDir || '').match(/\.pm\/([^/]+)(?:\/|$)/)
const _ra = String(args.rawArgs || '').replace(/--max-retries[=\s]+\d+/, ' ')
const _slugTok = _ra.trim().split(/\s+/).find(t => t && !t.startsWith('--'))
const slug = args.slug || (_td && _td[1]) || _slugTok || 'unknown'
log(`project = ${slug} (slug arg=${args.slug || '∅'}, tasksDir=${args.tasksDir || '∅'})`)

// --- Guard: if the inputs never arrived (e.g. args passed as an unparseable
//     string, or the orchestrator skipped Step 3.1), fail loud instead of
//     dispatching 'unknown'/'undefined' workers that quietly do the wrong thing.
const _missing = ['tasksDir', 'executeCmdPath', 'verifyCmdPath'].filter(k => !args[k])
if (slug === 'unknown' || _missing.length) {
  const detail = `slug='${slug}', missing=[${_missing.join(', ') || 'none'}], argsType=${typeof args}`
  log(`ABORT: /pm:auto inputs not populated — ${detail}. The orchestrator must pass args as a JSON object (Step 3.1/3.2), not a string.`)
  return { reason: 'bad-inputs', detail, completed: [], rejectionCapped: null, blocked: null, skippedClaimed: [], cycles: 0 }
}

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
  `You are a read-only status reader for /pm:auto, project '${slug}'. Be fast and frugal: do NOT read full task files — grep.\n` +
  `Task files are the '*.md' files in: ${args.tasksDir}\n` +
  `1. List the '*.md' task files there.\n` +
  `2. FRONTMATTER ONLY — read each file's top YAML block (between the first pair of '---' lines), ideally with one grep across all files, to get:\n` +
  `   - id: frontmatter 'id', else the leading number of the filename, zero-padded to 3\n` +
  `   - title: frontmatter 'title' (or the first heading)\n` +
  `   - status: frontmatter 'status' verbatim\n` +
  `   - depends_on: frontmatter 'depends_on' as an array of 3-digit id strings (empty array if none)\n` +
  `   - assignee: frontmatter 'assignee' verbatim, or null if absent/empty\n` +
  `3. SECTION PRESENCE by LITERAL heading grep — never by meaning:\n` +
  `   - hasBlocker: true ONLY if the body contains a line matching '^## Blocker' exactly. A '## Verifier notes — … — REJECTED' section is NOT a blocker — never set hasBlocker for it.\n` +
  `   - hasVerifierNotes: true if the body contains a line matching '^## Verifier notes'.\n` +
  `4. BODY TEXT only where the loop needs it — otherwise return null (do NOT read bodies for other tasks):\n` +
  `   - blockerText: ONLY when status is 'in-progress' AND hasBlocker — the text under '## Blocker'. Else null.\n` +
  `   - verifierNotesText: ONLY when status is 'rejected' — the text of the MOST RECENT '## Verifier notes' section. Else null.\n` +
  `Return one object per task with: id, title, status, depends_on, assignee, hasBlocker, blockerText, hasVerifierNotes, verifierNotesText.\n` +
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
  (t.status === 'pending' || t.status === 'rejected' ||
   (t.status === 'in-progress' && resumeAuthorized.includes(t.id))) &&
  (t.depends_on || []).every(d => byId[d] && byId[d].status === 'done')

while (true) {
  // (1) Disk is truth — a fresh, independent snapshot every iteration.
  let snap = await agent(snapshotPrompt, { schema: SNAPSHOT, model: 'sonnet', label: 'snapshot', phase: 'Loop' })
  let tasks = (snap && snap.tasks) || []
  if (tasks.length === 0) {
    // A non-empty tasks dir returning 0 tasks is a snapshot read failure, not a
    // finished project (pre-flight already exits early on a genuinely empty one).
    // Retry once before aborting loud — never let a bad read masquerade as 'done'.
    log(`[cycle ${cycle}] snapshot returned 0 tasks — retrying once`)
    snap = await agent(snapshotPrompt, { schema: SNAPSHOT, model: 'sonnet', label: 'snapshot-retry', phase: 'Loop' })
    tasks = (snap && snap.tasks) || []
    if (tasks.length === 0) {
      out.reason = 'snapshot empty'
      log(`ABORT: snapshot returned 0 tasks twice for ${args.tasksDir} — likely a read failure, not a finished project.`)
      break
    }
  }
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

## Step 3-P — Run the parallel loop (Workflow, only when `--parallel` is present)

Dispatch this script INSTEAD of the Step 3 serial script when `--parallel` (and not `--parallel 0|1`) was passed. Build the same `args` object as Step 3.1, including `integrationBranch`. Everything in Step 3.2/3.3 (pass `args` as a real JSON object; fall back to the serial in-context loop if the Workflow tool is missing) applies. The script differs from the serial one in three ways: (a) it runs up to N task pipelines concurrently via a continuous frontier scheduler; (b) each pipeline runs in isolated git worktrees and the execute worker commits to a per-task branch; (c) accepted work is merged back into `integrationBranch` serially, auto-resolving conflicts and re-checking the merged result.

The script (pass exactly as `script`):

```js
export const meta = {
  name: 'pm-auto-parallel',
  description: 'Autonomous parallel execute -> verify loop for a pm project, worktree-isolated with merge-back',
  phases: [{ title: 'Loop' }],
}

if (typeof args === 'string') { try { args = JSON.parse(args) } catch (e) { /* guard below reports */ } }

// --- Schemas (no filesystem access; every disk/git read is an agent) ---
const ONE = {
  type: 'object',
  required: ['id', 'status', 'depends_on'],
  properties: {
    id: { type: 'string' },
    status: { type: 'string' },
    depends_on: { type: 'array', items: { type: 'string' } },
    assignee: { type: ['string', 'null'] },
    branch: { type: ['string', 'null'] },
    hasBlocker: { type: 'boolean' },
    blockerText: { type: ['string', 'null'] },
    hasVerifierNotes: { type: 'boolean' },
    verifierNotesText: { type: ['string', 'null'] },
  },
}
const SNAPSHOT = { type: 'object', required: ['tasks'], properties: { tasks: { type: 'array', items: ONE } } }
const WORKER = { type: 'object', required: ['status', 'summary'], properties: { status: { type: 'string' }, summary: { type: 'string' }, branch: { type: ['string', 'null'] }, blockerText: { type: ['string', 'null'] } } }
const VERDICT = { type: 'object', required: ['verdict', 'status', 'summary'], properties: { verdict: { type: 'string' }, status: { type: 'string' }, summary: { type: 'string' } } }
const MERGE = { type: 'object', required: ['result'], properties: { result: { type: 'string' }, detail: { type: ['string', 'null'] } } }
const REVERDICT = { type: 'object', required: ['verdict'], properties: { verdict: { type: 'string' }, summary: { type: ['string', 'null'] } } }

// --- Resolve slug (same recovery as the serial script) ---
const _td = String(args.tasksDir || '').match(/\.pm\/([^/]+)(?:\/|$)/)
const _ra = String(args.rawArgs || '').replace(/--max-retries[=\s]+\d+/, ' ').replace(/--parallel(?:[=\s]+\d+)?/, ' ')
const _slugTok = _ra.trim().split(/\s+/).find(t => t && !t.startsWith('--'))
const slug = args.slug || (_td && _td[1]) || _slugTok || 'unknown'
const integrationBranch = String(args.integrationBranch || '').trim()
// Repo-relative tasks dir for the worktree-isolated execute/verify workers (their cwd
// is a separate working tree, so an absolute path baked to the main checkout would
// escape isolation). Derived from tasksDir's '.pm/...' tail; falls back to absolute.
const _tdRelMatch = String(args.tasksDir || '').match(/(\.pm\/.*)$/)
const tasksDirRel = String(args.tasksDirRel || (_tdRelMatch && _tdRelMatch[1]) || args.tasksDir || '').trim()
log(`project = ${slug}, integration branch = ${integrationBranch || '∅'}, tasks (rel) = ${tasksDirRel}`)

// --- Guard: inputs must be populated, AND parallel mode needs the integration branch ---
const _missing = ['tasksDir', 'executeCmdPath', 'verifyCmdPath'].filter(k => !args[k])
if (slug === 'unknown' || _missing.length || !integrationBranch) {
  const detail = `slug='${slug}', missing=[${_missing.join(', ') || 'none'}], integrationBranch='${integrationBranch}', argsType=${typeof args}`
  log(`ABORT: /pm:auto --parallel inputs not populated — ${detail}. The orchestrator must pass args as a JSON object (Step 3.1/3.2) including integrationBranch.`)
  return { reason: 'bad-inputs', detail, parallel: true, completed: [], blocked: [], rejectionCapped: [], anomalies: [], mergeFailed: [], unreachable: [], skippedClaimed: [], dispatched: 0 }
}

// --- Config parsed in code from rawArgs (never model-extracted) ---
const _mr = String(args.rawArgs || '').match(/--max-retries[=\s]+(\d+)/)
const maxRetries = _mr ? parseInt(_mr[1], 10) : (Number.isInteger(args.maxRetries) ? args.maxRetries : 2)
const _pf = String(args.rawArgs || '').match(/--parallel(?:[=\s]+(\d+))?/)
const reqN = _pf && _pf[1] ? parseInt(_pf[1], 10) : 3
const WORKFLOW_CAP = 10
const N = Math.max(1, Math.min(reqN, WORKFLOW_CAP))
log(`max-retries = ${maxRetries}, concurrency N = ${N}${_pf && _pf[1] ? '' : ' (default)'}`)

const me = String(args.gitEmail || '').toLowerCase()
const resumeAuthorized = Array.isArray(args.resumeAuthorized) ? args.resumeAuthorized : []
const skippedClaimed = Array.isArray(args.skippedClaimed) ? args.skippedClaimed.slice() : []

// --- Prompts. Workers derive the per-task branch from the task filename
//     (pm/<slug>/<filename-without-.md>), exactly the /pm:claim convention. ---
function executePrompt(id, resumeLine) {
  return [
    `You are an execute worker dispatched by /pm:auto --parallel for project '${slug}', task ${id}. You are running in a fresh, isolated git worktree the harness created for you — a separate working directory of this repo, and your cwd is its root. Nothing you do here can touch another worker's tree, so the git steps below are race-free. Use repo-relative paths (your cwd is the worktree root); do NOT use absolute paths into any other checkout.`,
    ``,
    `SETUP first: find the '*.md' file in ${tasksDirRel} whose name starts with '${id}-'; let BR = 'pm/${slug}/<that filename without .md>'. Base your work on the integration branch so completed dependencies are present: if BR already exists (a prior attempt) run 'git checkout ' + BR; otherwise run 'git checkout -b ' + BR + ' ${integrationBranch}'.`,
    ``,
    `Then invoke the Skill tool with skill 'pm:execute' and args '${slug} ${id}', and follow it fully. If the Skill tool is unavailable or 'pm:execute' is not available, instead Read '${args.executeCmdPath}' and follow its contents, treating $ARGUMENTS as '${slug} ${id}'.`,
    ``,
    `Rules: work ONLY task ${id} — never auto-pick another. Never pass --force. Do not run pm:verify or any other pm command. You cannot ask the user questions: take the safe default; if you cannot complete the task, follow pm:execute's blocker protocol exactly (leave status 'in-progress', write a '## Blocker' section with specifics) rather than improvising or flipping the status anyway.${resumeLine}`,
    ``,
    `FINISH (parallel-mode contract — this REPLACES the serial 'never commit' rule): your worktree is DISCARDED after you return, so the commit on BR is the ONLY durable record (the branch ref persists in the shared repo even though this worktree is removed). Persist your FINAL state whatever the outcome — the success case (status 'done-pending-verify') OR the blocker case (status 'in-progress' + a '## Blocker' section): write 'branch: ' + BR into the task file frontmatter, then 'git add -A && git commit -m "pm ${slug} ${id}"'. Do NOT push. Touch ONLY this task's files. The orchestrator reads your committed status from BR; an uncommitted blocker would be lost.`,
    ``,
    `Report back ONLY: the task's final frontmatter 'status', the branch BR, a one-line summary, and the '## Blocker' text verbatim if you wrote one.`,
  ].join('\n')
}
function verifyPrompt(id) {
  return [
    `You are an independent verifier dispatched by /pm:auto --parallel for project '${slug}', task ${id}. You are running in a fresh, isolated git worktree the harness created for you — a separate working directory of this repo with no uncommitted changes, and your cwd is its root. Use repo-relative paths; do NOT use absolute paths into any other checkout.`,
    ``,
    `SETUP first: find the '*.md' file in ${tasksDirRel} whose name starts with '${id}-'; let BR be its 'branch:' frontmatter value (or 'pm/${slug}/<that filename without .md>'). Check out BR's tip in DETACHED HEAD so it doesn't matter whether another worktree still holds BR: 'git checkout --detach ' + BR. Review the work as the COMMITTED diff of BR against the integration branch — 'git diff ${integrationBranch}...HEAD' — NOT the uncommitted working tree.`,
    ``,
    `Then invoke the Skill tool with skill 'pm:verify' and args '${slug} ${id}', and follow it fully. If the Skill tool is unavailable or 'pm:verify' is not available, instead Read '${args.verifyCmdPath}' and follow its contents, treating $ARGUMENTS as '${slug} ${id}'.`,
    ``,
    `Rules: verify ONLY task ${id}. You did not write this code; judge it cold. Never modify implementation files — only the task file, per pm:verify. If borderline, REJECT with specific notes. After pm:verify writes the task file (status + '## Verifier notes'), commit that change onto BR and move BR to it: 'git add -A && git commit -m "pm ${slug} ${id} verify" && git branch -f ' + BR + ' HEAD' (you are detached, so update BR explicitly) so the result is durable on the branch. Never push.`,
    ``,
    `Report back ONLY: the verdict (ACCEPT/REJECT), the task's final frontmatter 'status', and a one-line summary.`,
  ].join('\n')
}
function mergePrompt(id) {
  return [
    `You are a merge worker for /pm:auto --parallel, project '${slug}', task ${id}. You operate in the MAIN working tree, which is on the integration branch '${integrationBranch}'. Do NOT create a worktree.`,
    ``,
    `Find the '*.md' file in ${args.tasksDir} whose name starts with '${id}-'; let BR be its 'branch:' frontmatter value (or 'pm/${slug}/<that filename without .md>'). Ensure you are on the integration branch ('git checkout ${integrationBranch}'), then merge: 'git merge --no-ff ' + BR + ' -m "pm ${slug} ${id} merge"'.`,
    ``,
    `- Clean merge → report result='clean'.`,
    `- Conflicts → resolve them faithfully to BOTH sides' intent (the integration branch already holds other accepted tasks' work; preserve that AND task ${id}'s changes), then 'git add -A && git commit --no-edit' to complete the merge, and report result='resolved' with a one-line 'detail' of what you reconciled.`,
    `- Cannot resolve safely → 'git merge --abort' and report result='failed' with 'detail'.`,
    ``,
    `Never push. Report ONLY: result ('clean'|'resolved'|'failed') and detail.`,
  ].join('\n')
}
function reverifyPrompt(id) {
  return [
    `You are an advisory re-verifier for /pm:auto --parallel, project '${slug}', task ${id}, checking the MERGED result. You operate in the MAIN working tree on '${integrationBranch}' (task ${id}'s merge is the current HEAD). Do NOT create a worktree.`,
    ``,
    `Read the task file and the criteria pm:verify would use, and judge whether task ${id}'s acceptance criteria STILL hold in the merged tree — a textual merge can break things semantically. Run the task's test command if its '## Implementation summary' specifies one.`,
    ``,
    `This is an ADVISORY check only: do NOT modify any file, do NOT change status, do NOT write verifier notes. If the merged result is sound, verdict=ACCEPT; if the merge broke task ${id}, verdict=REJECT with a one-line summary.`,
    ``,
    `Report ONLY: verdict (ACCEPT/REJECT) and summary.`,
  ].join('\n')
}
function readOnePrompt(id) {
  return [
    `Read-only status reader for /pm:auto --parallel, project '${slug}', task ${id}. Be fast: grep, don't read full bodies.`,
    `Find the '*.md' file in ${args.tasksDir} whose name starts with '${id}-'; let BR = 'pm/${slug}/<that filename without .md>'.`,
    `Source of truth: if branch BR exists ('git rev-parse --verify ' + BR succeeds), read the task's frontmatter and section presence from BR's tip via 'git show ' + BR + ':<repo-relative path to the task file>'. Otherwise read it from the working tree.`,
    `Return: id; status (frontmatter verbatim); depends_on (array of 3-digit id strings, [] if none); assignee (verbatim or null); branch (the 'branch:' field or null); hasBlocker (true ONLY if body has a line matching '^## Blocker'); blockerText (the text under '## Blocker' ONLY when status is 'in-progress' and hasBlocker, else null); hasVerifierNotes (body has '^## Verifier notes'); verifierNotesText (text of the MOST RECENT '## Verifier notes' ONLY when status is 'rejected', else null).`,
    `READ ONLY — modify nothing.`,
  ].join('\n')
}
const snapshotPrompt =
  `You are a read-only status reader for /pm:auto --parallel, project '${slug}'. Read from the integration branch's working tree (the current checkout). Be fast and frugal — grep, do NOT read full task files.\n` +
  `Task files are the '*.md' files in: ${args.tasksDir}\n` +
  `For each, from the top YAML frontmatter block, return: id (frontmatter 'id' else leading filename number zero-padded to 3); status; depends_on (array of 3-digit id strings, [] if none); assignee (verbatim or null); branch (the 'branch:' field or null); and by LITERAL heading grep hasBlocker ('^## Blocker') and hasVerifierNotes ('^## Verifier notes'). Set blockerText/verifierNotesText to null here. Return every task. READ ONLY.`

const readOne = (id) => agent(readOnePrompt(id), { schema: ONE, model: 'sonnet', label: `read:${id}`, phase: 'Loop' })

// --- Seed the dependency graph from the integration branch (disk truth at start) ---
let snap = await agent(snapshotPrompt, { schema: SNAPSHOT, model: 'sonnet', label: 'snapshot', phase: 'Loop' })
let tasks = (snap && snap.tasks) || []
if (tasks.length === 0) {
  snap = await agent(snapshotPrompt, { schema: SNAPSHOT, model: 'sonnet', label: 'snapshot-retry', phase: 'Loop' })
  tasks = (snap && snap.tasks) || []
}
if (tasks.length === 0) {
  log(`ABORT: snapshot returned 0 tasks twice for ${args.tasksDir} — likely a read failure, not a finished project.`)
  return { reason: 'snapshot empty', parallel: true, completed: [], blocked: [], rejectionCapped: [], anomalies: [], mergeFailed: [], unreachable: [], skippedClaimed, dispatched: 0 }
}
const byId = {}
for (const t of tasks) byId[t.id] = t
const done = new Set(tasks.filter(t => t.status === 'done').map(t => t.id))

const heldByOther = (a) => !!a && !String(a).toLowerCase().includes(me)
const isReady = (t) =>
  (t.status === 'pending' || t.status === 'rejected' ||
   (t.status === 'in-progress' && resumeAuthorized.includes(t.id))) &&
  (t.depends_on || []).every(d => done.has(d)) &&
  !heldByOther(t.assignee)

// --- Serialized merge-back with auto-resolve (the confirmed integration policy) ---
let mergeChain = Promise.resolve()
function mergeBack(id) {
  const run = async () => {
    const m = await agent(mergePrompt(id), { schema: MERGE, model: 'sonnet', label: `merge:${id}`, phase: 'Loop' })
    if (m.result === 'clean') return { id, outcome: 'accepted', merged: 'clean' }
    if (m.result === 'resolved') {
      const rv = await agent(reverifyPrompt(id), { schema: REVERDICT, model: 'opus', label: `reverify:${id}`, phase: 'Loop' })
      const ok = rv && String(rv.verdict).toUpperCase().startsWith('ACCEPT')
      return ok ? { id, outcome: 'accepted', merged: 'resolved' }
                : { id, outcome: 'merge-failed', text: `re-verify rejected merged result: ${rv && rv.summary || ''}` }
    }
    return { id, outcome: 'merge-failed', text: (m && m.detail) || 'merge could not be completed' }
  }
  const p = mergeChain.then(run, run)   // serialize regardless of the previous merge's outcome
  mergeChain = p.then(() => {}, () => {})
  return p
}

// --- Per-task pipeline: execute -> verify -> (retry) -> merge. Disk (the task
//     branch) is truth; the worker's structured return is advisory. ---
function runTask(id) {
  return (async () => {
    let rej = 0
    while (true) {
      const resumeLine = resumeAuthorized.includes(id)
        ? `\n\nThe user has already approved redoing this in-progress task — proceed past the redo confirmation.` : ''
      await agent(executePrompt(id, resumeLine), { schema: WORKER, model: 'sonnet', isolation: 'worktree', label: `execute:${id}`, phase: 'Loop' })
      const e = await readOne(id)
      if (e.status === 'in-progress' && e.hasBlocker) { log(`task ${id} — execute ⊘ BLOCKED`); return { id, outcome: 'blocker', text: e.blockerText } }
      if (e.status !== 'done-pending-verify') { log(`task ${id} — execute ✗ ANOMALY (${e.status})`); return { id, outcome: 'anomaly', text: `execute left status '${e.status}'` } }

      await agent(verifyPrompt(id), { schema: VERDICT, model: 'opus', isolation: 'worktree', label: `verify:${id}`, phase: 'Loop' })
      const v = await readOne(id)
      if (v.status === 'rejected') {
        rej++
        log(`task ${id} — verify ✗ REJECTED (retry ${rej}/${maxRetries})`)
        if (rej >= maxRetries) return { id, outcome: 'retry-capped', rejections: rej, notes: v.verifierNotesText }
        continue   // re-execute; the worker reuses BR and reads '## Verifier notes' from disk
      }
      if (v.status !== 'done') { log(`task ${id} — verify ✗ ANOMALY (${v.status})`); return { id, outcome: 'anomaly', text: `verify left status '${v.status}'` } }

      log(`task ${id} — verify ✓ ACCEPTED → merging`)
      const r = await mergeBack(id)
      if (r.outcome === 'accepted') log(`task ${id} — merged (${r.merged}) ✓`)
      else log(`task ${id} — merge ✗ ${r.text || ''}`)
      return r
    }
  })()
}

// --- Continuous frontier scheduler: keep up to N pipelines in flight, refilling
//     the instant any task finishes (Promise.race), so a freed slot is reused
//     immediately rather than waiting for a whole batch (level-barrier) to drain. ---
const results = {}
const inflight = new Map()   // id -> Promise<{id, ...outcome}>
const eligibleNow = () => tasks.filter(t =>
  !done.has(t.id) && !(t.id in results) && !inflight.has(t.id) && isReady(t))
function fill() {
  for (const t of eligibleNow()) {
    if (inflight.size >= N) break
    if (heldByOther(t.assignee) && !skippedClaimed.find(s => s.id === t.id)) skippedClaimed.push({ id: t.id, owner: t.assignee })
    inflight.set(t.id, runTask(t.id))
  }
}
let dispatched = 0
const guard = tasks.length * (maxRetries + 2) + 50
fill()
while (inflight.size > 0) {
  if (++dispatched > guard) { log(`ABORT: scheduler guard (${guard}) exceeded — likely a loop bug.`); break }
  const r = await Promise.race(inflight.values())
  inflight.delete(r.id)
  results[r.id] = r
  if (r.outcome === 'accepted') { byId[r.id].status = 'done'; done.add(r.id) }
  fill()
}

// --- Aggregate outcomes (parallel mode drains in-flight work, then reports ALL). ---
const ofKind = (k) => Object.values(results).filter(r => r.outcome === k)
const completed = ofKind('accepted').map(r => r.id).sort()
const blocked = ofKind('blocker').map(r => ({ id: r.id, text: r.text }))
const rejectionCapped = ofKind('retry-capped').map(r => ({ id: r.id, rejections: r.rejections, notes: r.notes }))
const anomalies = ofKind('anomaly').map(r => ({ id: r.id, text: r.text }))
const mergeFailed = ofKind('merge-failed').map(r => ({ id: r.id, text: r.text }))
const unreachable = tasks.filter(t => !done.has(t.id) && !(t.id in results) && !heldByOther(t.assignee)).map(t => t.id).sort()
const allDone = tasks.every(t => done.has(t.id))
const failures = blocked.length + rejectionCapped.length + anomalies.length + mergeFailed.length
const reason = allDone ? 'all tasks done'
  : failures > 0 ? 'drained — see blocked / rejection-capped / anomalies / merge-failed'
  : 'no eligible tasks'

return { reason, parallel: true, concurrency: N, completed, blocked, rejectionCapped, anomalies, mergeFailed, unreachable, skippedClaimed, dispatched }
```

When this Workflow returns, go to Step 6 and print the parallel summary from the returned object.

## Step 4 — Subagent worker prompts

These are the prompts the loop dispatches (embedded in the Step 3 script as `executePrompt` / `verifyPrompt`, and used verbatim by the Fallback loop). Keep the two copies in sync. Both run as `subagent_type: general-purpose`, one at a time; the per-agent `model` preserves the plugin's tiering. The **parallel-mode** variants (embedded in the Step 3-P script) differ and are documented separately at the end of this section — keep those in sync with the Step 3-P script too.

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

### Parallel-mode worker prompts (Step 3-P only)

In `--parallel` mode the same execute/verify intent applies, but each worker runs in an isolated git worktree and the work is carried on a per-task branch `BR = pm/<slug>/<task-filename-without-.md>` (the `/pm:claim` convention) instead of as uncommitted edits. There are two extra worker roles (merge, re-verify) that operate in the MAIN working tree, not a worktree. Disk-is-truth is preserved by reading each task's frontmatter **from its branch** (`git show BR:<path>`).

**Execute (parallel, `model: sonnet`)** — as the serial execute worker, except: it first checks out/creates `BR` based on `<integrationBranch>` (so completed dependencies are present), and the "never commit" rule is replaced by — once the task is `done-pending-verify`, write `branch: BR` into the task frontmatter and `git add -A && git commit` on `BR` (never push). This commit is how the verifier and merge step consume the work.

**Verify (parallel, `model: opus`)** — as the serial verify worker, except: it `git checkout BR` and reviews the committed diff `git diff <integrationBranch>...HEAD` (not the uncommitted tree), then commits its task-file change (status + `## Verifier notes`) on `BR` so the verdict is durable on the branch.

**Merge (parallel, `model: sonnet`)** — operates in the MAIN tree on `<integrationBranch>`; `git merge --no-ff BR`. Clean → report `clean`. Conflicts → resolve faithfully to both sides (preserve already-merged tasks' work AND this task's), commit the merge, report `resolved`. Unresolvable → `git merge --abort`, report `failed`. Never push.

**Re-verify (parallel, `model: opus`)** — advisory only, MAIN tree on the post-merge `<integrationBranch>` HEAD; judges whether the task's acceptance criteria still hold after the textual merge (runs the task's tests if specified). Modifies nothing, writes no status/notes. Reports `ACCEPT`/`REJECT`. Fires only after a conflict-`resolved` merge.

## Step 5 — Stop conditions

The loop computes these in code (Step 3 script) from each fresh snapshot. It stops and runs Step 6 when any fires:

- **All done** — no eligible ready and no done-pending-verify tasks remain, and every task is `done`. (`reason: 'all tasks done'`)
- **Retry cap** — a task's rejection count reaches `max_retries`. Print its latest `## Verifier notes — <date> — REJECTED` section verbatim (carried as `rejectionCapped.notes`). A repeatedly-failing task usually signals a planning or criteria problem; its dependents are blocked anyway. Hint: `/pm:execute <slug> <NNN>` for a supervised retry.
- **Blocker** — execute worker left `in-progress` + `## Blocker`. Print the blocker verbatim (`blocked.text`). Hint: resolve it, then re-run `/pm:auto <slug>` — pre-flight will offer to resume the task.
- **No eligible tasks** — ready tasks exist but all are claimed by others, or pending tasks are blocked behind skipped/claimed ones. Report as "no eligible tasks", NOT "all done" — list who holds what (`skippedClaimed`).
- **Cycle cap** — `max_cycles` reached. This almost certainly indicates a bug worth reporting.
- **Snapshot empty** — the snapshot agent returned 0 tasks twice in a row for a non-empty tasks dir. A read failure, NOT a finished project; the loop aborts loud rather than masquerading as "no eligible tasks". (`reason: 'snapshot empty'`) Hint: re-run `/pm:auto <slug>`; if it persists, the snapshot read is broken.
- **Anomaly** — a worker died mid-work, refused, or failed (disk status didn't advance as expected). Surface the worker's state.

**Parallel mode (Step 3-P) differs in one key way: a per-task failure does NOT halt the run.** Serial mode stops at the first blocker / retry-cap / anomaly. Parallel mode lets every in-flight pipeline **drain**, then reports ALL outcomes together — so one task's blocker doesn't waste sibling work already running. The aggregate `reason` is `'all tasks done'` only when every task is `done`; otherwise it surfaces the full sets `blocked[]`, `rejectionCapped[]`, `anomalies[]`, and the parallel-only:
- **Merge failed** — a task was ACCEPTED on its branch but could not be integrated: the merge worker couldn't resolve a conflict, or the post-resolution re-verify rejected the merged result. The task branch is left intact for manual integration. (`mergeFailed[]`)
- **Unreachable** — a task never became eligible because a dependency failed (blocked/capped/anomaly/merge-failed). Reported so it's clear why it didn't run. (`unreachable[]`)

## Step 6 — Final summary

Always printed by you (the orchestrator) when the Workflow returns, whatever the stop reason:

```
/pm:auto finished — <reason: all tasks done | retry cap hit on 004 | blocker on 006 | no eligible tasks | cycle cap hit | snapshot empty | anomaly>
Cycles run:        7
Completed:         003, 004, 005
Rejection-capped:  —  (or: 004 — 2 rejections, see ## Verifier notes)
Skipped (claimed): 002 (Alice <a@example.com>)
Blocked:           —  (or: 006 — see ## Blocker)
Next: /pm:release <slug>   (only when every task in the active version is done;
      otherwise a stop-reason-appropriate hint: /pm:execute <slug> <NNN>, /pm:status <slug>, …)
```

**Parallel mode (Step 3-P)** returns the aggregate object instead; print all non-empty sets:

```
/pm:auto --parallel finished — <reason>   (concurrency 3)
Completed (merged): 001, 002, 004
Rejection-capped:   005 — 2 rejections, see ## Verifier notes
Blocked:            —  (or: 006 — see ## Blocker)
Anomalies:          —
Merge-failed:       003 — conflict on src/gateway.ts re-verify rejected; branch pm/<slug>/003-… left for manual merge
Unreachable:        007 (depends on 005)
Skipped (claimed):  —
Next: /pm:complete <slug> <NNN> per completed task to open PRs (parallel mode leaves accepted work
      committed on your branch and on per-task branches; it does not push or open PRs itself).
      Resolve any merge-failed branches manually, then re-run /pm:auto <slug> for the rest.
```

Accepted work in parallel mode is already committed on `integrationBranch` (and on each task branch); `/pm:complete` will push + open the PR per task. There is no uncommitted working tree to lose.

## Fallback loop (only when the Workflow tool is unavailable)

This fallback is **serial-only**. If `--parallel` was requested but the Workflow tool is unavailable, print a one-line notice ("parallel mode needs the Workflow tool; running sequentially") and run this serial loop — an in-context model cannot safely drive concurrent git worktrees.

Run the loop yourself, in this context. **Continuation contract — read this first:** after EVERY subagent tool result your turn is **not** over. Your immediate next action is exactly one of: (a) dispatch the next subagent, or (b) print the Step 6 summary because a Step 5 stop condition fired. Ending your turn in any other situation — eligible tasks remaining, no stop condition met — is a defect, not a stopping point. Do not narrate, summarize progress, or yield between cycles; just continue.

Initialize session state: a rejection map (`task-id → rejections_this_session`, all 0) and a cycle cap `max_cycles = (tasks not yet done) × (max_retries + 1) + (count of done-pending-verify tasks) + 3`.

Repeat until a Step 5 stop condition fires:

**3a. Pick the phase.** Any `done-pending-verify` task → **verify phase** on the lowest id (drains pre-existing backlog first). Else the lowest-id **eligible** ready task → **execute phase**. Ready = status `pending`/`rejected` (or `in-progress` when the id is in `resume_authorized`) AND every `depends_on` id is `done`, MINUS tasks whose `assignee` is someone other than the current git identity (record those in `skipped_claimed`). NEVER pass `--force`. Else → stop (no eligible tasks).

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
- The verifier-independence guarantee survives automation: the verify subagent never shares context with the executor that produced the work. In `--parallel` mode it is *strengthened* — each execute and verify worker runs in a real, harness-created git worktree (dispatched with `isolation: 'worktree'`), a genuinely separate working directory, so concurrent workers cannot share or race on a working tree. The main checkout is never touched by workers; only the serialized merge step writes there.
- The control loop holds only counters and per-cycle status lines — no diffs, no implementation detail, no verification reasoning. Even the worker's structured return is advisory; flow decisions come only from the fresh on-disk read (the working tree in serial mode; the task's branch via `git show` in parallel mode).

## Output discipline
- Never pass `--force` to anything. Never claim, complete, or release.
- Never edit task files yourself — subagents own all status flips. The loop only reads (via the snapshot/read agents).
- Disk is truth: re-read frontmatter every iteration; worker reports are advisory.
- **Serial mode:** serial dispatch only — concurrent worker calls are a bug; don't commit/push, and don't let subagents commit/push.
- **Parallel mode (`--parallel`):** up to N concurrent task pipelines, each in its own worktree. The "never commit" rule is relaxed to "execute/verify workers commit to the per-task branch `BR`, the merge worker commits the merge to `integrationBranch`, **nobody ever pushes**." Merges into `integrationBranch` are serialized (one at a time). This is the only mode where `/pm:auto` writes git history.
- Surface failures verbatim (`## Blocker`, `## Verifier notes`) — don't paraphrase them away.

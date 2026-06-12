---
description: Autonomously run the full authoring pipeline (prd → research → architect → test → plan), each stage in an isolated --auto subagent, then hand off to /pm:auto.
model: sonnet
argument-hint: <one-line idea> | <slug> [--force]
---

# /pm:autoplan — Autonomous authoring pipeline

You are running the `/pm:autoplan` command. You are the **orchestrator**. You do NOT write the PRD, research, architecture, test strategy, or tasks yourself — you sequence the pipeline stages, dispatch each as a fresh isolated subagent that invokes the real pipeline command with `--auto`, re-check state from disk between stages, and decide whether to continue.

The pipeline is linear: `prd → research → architect → test → plan`. Each stage runs the corresponding `/pm:<stage>` command in **override mode** (`--auto`), so every stage makes best-judgment decisions instead of interviewing the user. When the last stage lands task files on disk, the project is ready to execute — hand off to `/pm:auto <slug>`.

This is the planning-phase sibling of `/pm:auto`: `/pm:autoplan` takes an idea to tasks; `/pm:auto` takes tasks to done. Together: **idea → tasks (`/pm:autoplan`) → done (`/pm:auto`)**.

The pipeline runs as a **deterministic Workflow** (Step 3): a real code loop drives the stages in order, so it cannot spuriously stop between them the way a prose loop can. If the Workflow tool is unavailable in this environment, fall back to the hardened in-context pipeline at the end of this file.

This command covers ONLY the authoring phase. It never claims, executes, verifies, completes, or releases.

> **Not `/pm:express`.** `/pm:express` is a *compressed, single-context, interactive* fast path for **small** projects (one PM persona, light/no research, deferred architecture, 1–5 tasks). `/pm:autoplan` runs the **full-rigor** pipeline — the real two-persona PRD, the real multi-persona research, full architecture and test strategy — with each stage isolated in its own subagent and no human in the loop. Use express for small work you want to shape by hand; use autoplan to drive a full project to tasks unattended.

## Inputs
Parse `$ARGUMENTS`:
- `--force` (anywhere) → re-run stages whose artifact already exists (each underlying command's `--auto` takes the overwrite-with-backup path). Default (no `--force`) = **skip** any stage whose artifact is already on disk (resume semantics).
- The remaining text (after removing `--force`) is the idea-or-slug:
  - If it names an existing `.pm/<slug>/` directory → **resume mode** (slug known; pick up from the first missing stage).
  - Else if non-empty → **idea mode**: the text is the one-line idea seed; the `prd` stage creates the slug.
  - Else empty → **hard blocker**: STOP with "autoplan needs a one-line idea (fresh) or an existing slug (resume)." Launch no workflow.

You do NOT extract `--force` yourself for the Workflow logic beyond setting the `force` boolean in `args` — pass it through and the deterministic script applies it.

## Step 1 — Resolve mode and version

- **Idea mode:** there is no project yet. `version` = `v1` (prd scaffolds `v1`). `slug` is unknown — the prd stage produces it.
- **Resume mode:** read `active_version` from `.pm/<slug>/prd.md` frontmatter (default `v1`). The slug is known.

Read the current git identity once is NOT needed here — autoplan never claims or touches assignees.

## Step 2 — Pre-flight presence snapshot

This is the only pre-loop moment; after it, the pipeline runs unattended.

- **Idea mode:** nothing exists yet — every `present.*` flag is `false`.
- **Resume mode:** inventory `.pm/<slug>/<active_version>/` and record which artifacts already exist:
  - `research` — true if `research/` contains any `*.md` file.
  - `architecture` — true if `architecture.md` exists.
  - `testing` — true if `testing.md` exists.
  - `tasks` — true if `tasks/` contains any `*.md` file.

These flags drive stage-skipping in the loop (skip a stage whose artifact is present, unless `--force`). If resume mode finds every stage already present and `--force` is absent, the pipeline will simply skip through to `already-planned` and hand off.

## Step 3 — Run the pipeline (Workflow)

The pipeline is a deterministic Workflow. By instructing you to call the Workflow tool, this command is your explicit opt-in to use it — call it directly; do not ask the user first.

**3.1 — Build the inputs.** Resolve the plugin command paths (`${CLAUDE_PLUGIN_ROOT}` is expanded here, in the command — the Workflow script cannot expand env vars itself) and the absolute `.pm` directory. Assemble the `args` object:

```
args = {
  mode:             "<idea | resume>",
  idea:             "<the one-line idea seed, or '' in resume mode>",
  slug:             "<slug in resume mode, or '' in idea mode>",
  version:          "<active_version, e.g. 'v1'>",
  pmDir:            "<abs path to .pm>",
  force:            <true if --force was passed, else false>,
  present:          { research: <bool>, architecture: <bool>, testing: <bool>, tasks: <bool> },
  prdCmdPath:       "${CLAUDE_PLUGIN_ROOT}/commands/prd.md",
  researchCmdPath:  "${CLAUDE_PLUGIN_ROOT}/commands/research.md",
  architectCmdPath: "${CLAUDE_PLUGIN_ROOT}/commands/architect.md",
  testCmdPath:      "${CLAUDE_PLUGIN_ROOT}/commands/test.md",
  planCmdPath:      "${CLAUDE_PLUGIN_ROOT}/commands/plan.md",
}
```

**3.2 — Dispatch the pipeline.** Call the **Workflow tool** with the `args` above and the `script` below verbatim. **Pass `args` as an actual JSON object value, NOT a JSON-encoded string** — if you stringify it, every `args.X` read inside the script is `undefined` and stage workers get dispatched with project `'unknown'` / path `'undefined'`. (The script also defensively `JSON.parse`s a stringified `args` as a backstop, but pass an object regardless.) The Workflow runs in the background; per-stage progress is visible live via `/workflows`, and you are re-invoked when it finishes. When it returns its result object, print the Step 6 summary from it.

**3.3 — Fallback.** If the Workflow tool is not available in this environment, do NOT improvise — follow the **Fallback pipeline** section at the end of this file instead.

The script (pass exactly as `script`):

```js
export const meta = {
  name: 'pm-autoplan',
  description: 'Autonomous authoring pipeline (prd -> research -> architect -> test -> plan) for a pm project',
  phases: [{ title: 'Pipeline' }],
}

// --- Normalize args: some orchestrators serialize the args object to a JSON
//     string before passing it to the Workflow tool. When that happens, every
//     args.X read is undefined (a string has no such property) and workers get
//     dispatched with project 'unknown' / path 'undefined'. Parse it back so
//     the pipeline is robust to that, regardless of how the model fills the input.
if (typeof args === 'string') { try { args = JSON.parse(args) } catch (e) { /* leave as-is; guard below reports */ } }

// --- Schemas (the script has no filesystem access; every disk read is an agent) ---
const PRD_RESULT = {
  type: 'object',
  required: ['status', 'slug'],
  properties: {
    status: { type: 'string' },            // 'created' | 'blocked' | other
    slug: { type: ['string', 'null'] },    // slug read from prd.md frontmatter on disk
    summary: { type: ['string', 'null'] },
  },
}
const STAGE_RESULT = {
  type: 'object',
  required: ['status'],
  properties: {
    status: { type: 'string' },            // 'done' | 'blocked' | 'stopped' | other
    summary: { type: ['string', 'null'] },
  },
}
const EXISTS = {
  type: 'object',
  required: ['exists'],
  properties: {
    exists: { type: 'boolean' },
    detail: { type: ['string', 'null'] },
  },
}

// --- Guard: if the core inputs never arrived, fail loud rather than dispatching
//     'unknown'/'undefined' workers that quietly do the wrong thing. ---
const _missingCore = ['mode', 'version', 'pmDir', 'prdCmdPath', 'researchCmdPath', 'architectCmdPath', 'testCmdPath', 'planCmdPath'].filter(k => !args[k])
if (_missingCore.length) {
  const detail = `missing=[${_missingCore.join(', ')}], argsType=${typeof args}`
  log(`ABORT: /pm:autoplan inputs not populated — ${detail}. The orchestrator must pass args as a JSON object (Step 3.1/3.2), not a string.`)
  return { reason: 'bad-inputs', detail, slug: args.slug || null, stagesRun: [], stagesSkipped: [], produced: [] }
}

const mode = args.mode
const idea = String(args.idea || '')
const version = args.version
const pmDir = String(args.pmDir || '.pm')
const force = !!args.force
const present = args.present || {}
let slug = args.slug || null

if (mode === 'idea' && !idea.trim()) {
  log(`ABORT: idea mode with no idea seed — the command pre-flight should have stopped this.`)
  return { reason: 'prd-blocked', detail: 'no idea seed', slug, stagesRun: [], stagesSkipped: [], produced: [] }
}

log(`mode = ${mode}, slug = ${slug || '∅ (prd will create it)'}, version = ${version}, force = ${force}`)

// --- Worker prompts (mirror Step 4; only stage + slug/idea cross the boundary) ---
function stageWorkerPrompt(stage, cmdPath, argline) {
  return [
    `You are a ${stage} worker dispatched by /pm:autoplan${slug ? ` for project '${slug}'` : ''}.`,
    ``,
    `Invoke the Skill tool with skill 'pm:${stage}' and args '${argline}', and follow that command fully. If the Skill tool is unavailable or 'pm:${stage}' is not in your available skills, instead Read the file '${cmdPath}' and follow its contents as your instructions, treating $ARGUMENTS as '${argline}'.`,
    ``,
    `Rules: run ONLY the ${stage} stage. Never commit or push. Do not run any other pm command. The '--auto' flag in your args already authorizes you to make best-judgment decisions instead of asking the user — but do NOT improvise past a genuine hard blocker (e.g. a missing REQUIRED input); surface it and stop, leaving the artifact unwritten.`,
    ``,
    stage === 'prd'
      ? `When finished, report back ONLY: status ('created' if prd.md was written, 'blocked' if a hard blocker stopped you), and the project slug exactly as written in the 'slug:' field of the created prd.md frontmatter on disk (null if none was created).`
      : `When finished, report back ONLY: status ('done' if the stage's artifact was written, 'stopped'/'blocked' otherwise) and a one-line summary. Everything downstream reads from disk.`,
  ].join('\n')
}

function existsPrompt(relPath, kind) {
  // kind: 'file' (exact path) | 'glob' (any *.md under a dir)
  const base = `${pmDir}/${slug}/${version}`
  const target = kind === 'glob'
    ? `any '*.md' file inside the directory '${base}/${relPath}'`
    : `the file '${base}/${relPath}'`
  return `You are a read-only presence checker for /pm:autoplan, project '${slug}'. Determine whether ${target} exists. Be fast: just check existence, do not read contents. Return { exists: true|false, detail: "<path or note>" }. READ ONLY — modify nothing.`
}

function prdExistsPrompt(s) {
  return `You are a read-only presence checker for /pm:autoplan. Determine whether BOTH '${pmDir}/${s}/prd.md' AND '${pmDir}/${s}/${version}/goals.md' exist. Be fast: existence only. Return { exists: true|false, detail: "<which are present/missing>" }. READ ONLY — modify nothing.`
}

// --- Stage definitions in fixed pipeline order ---
const STAGES = [
  { name: 'prd',       cmd: args.prdCmdPath,       artifact: { rel: 'prd.md',       kind: 'file' } },
  { name: 'research',  cmd: args.researchCmdPath,  artifact: { rel: 'research',     kind: 'glob' } },
  { name: 'architect', cmd: args.architectCmdPath, artifact: { rel: 'architecture.md', kind: 'file' } },
  { name: 'test',      cmd: args.testCmdPath,      artifact: { rel: 'testing.md',   kind: 'file' } },
  { name: 'plan',      cmd: args.planCmdPath,      artifact: { rel: 'tasks',        kind: 'glob' } },
]

const stagesRun = []
const stagesSkipped = []
const produced = []
const out = { reason: null, slug, stagesRun, stagesSkipped, produced }

for (const st of STAGES) {
  // (1) Decide skip.
  if (st.name === 'prd') {
    if (mode === 'resume') { stagesSkipped.push('prd (already present)'); log(`stage prd — skipped (resume: PRD already exists)`); continue }
  } else {
    const presentKey = st.name === 'architect' ? 'architecture' : st.name === 'test' ? 'testing' : st.name === 'plan' ? 'tasks' : 'research'
    if (present[presentKey] && !force) {
      stagesSkipped.push(`${st.name} (already present)`)
      log(`stage ${st.name} — skipped (artifact present; pass --force to re-run)`)
      // plan-specific: tasks already exist means there's nothing left to author.
      continue
    }
  }

  // (2) Need a slug for every non-prd stage.
  if (st.name !== 'prd' && !slug) {
    out.reason = 'anomaly'; out.failedStage = st.name
    log(`ABORT: stage ${st.name} needs a slug but none was resolved.`); break
  }

  // (3) Dispatch ONE stage worker, serially. Continuation is the loop; the model never decides to stop here.
  if (st.name === 'prd') {
    const res = await agent(stageWorkerPrompt('prd', st.cmd, `${idea} --auto`), { schema: PRD_RESULT, model: 'opus', label: 'stage:prd', phase: 'Pipeline' })
    const reported = res && res.slug ? String(res.slug).trim() : null
    if (reported) slug = reported
    out.slug = slug
    // Disk is truth: confirm prd.md + goals.md actually landed for the slug we'll use downstream.
    if (!slug) { out.reason = 'prd-blocked'; log(`stage prd — ✗ no slug produced (blocked?)`); break }
    const chk = await agent(prdExistsPrompt(slug), { schema: EXISTS, model: 'haiku', label: 'check:prd', phase: 'Pipeline' })
    if (!chk || !chk.exists) {
      out.reason = (res && res.status === 'blocked') ? 'prd-blocked' : 'anomaly'; out.failedStage = 'prd'
      log(`stage prd — ✗ ${out.reason} (prd.md/goals.md not found for slug '${slug}')`); break
    }
    stagesRun.push('prd'); produced.push('prd.md', 'goals.md')
    log(`stage prd — ✓ created project '${slug}'`)
  } else {
    await agent(stageWorkerPrompt(st.name, st.cmd, `${slug} --auto`), { schema: STAGE_RESULT, model: 'opus', label: `stage:${st.name}`, phase: 'Pipeline' })
    // Disk is truth: confirm the stage's artifact landed.
    const chk = await agent(existsPrompt(st.artifact.rel, st.artifact.kind), { schema: EXISTS, model: 'haiku', label: `check:${st.name}`, phase: 'Pipeline' })
    if (!chk || !chk.exists) {
      out.reason = 'anomaly'; out.failedStage = st.name
      log(`stage ${st.name} — ✗ ANOMALY (expected artifact '${st.artifact.rel}' not found)`); break
    }
    stagesRun.push(st.name)
    produced.push(st.artifact.kind === 'glob' ? `${st.artifact.rel}/` : st.artifact.rel)
    log(`stage ${st.name} — ✓ done`)
  }
}

if (!out.reason) {
  // Reached the end with no stop. Distinguish "we authored tasks" from "everything was already there".
  out.reason = stagesRun.includes('plan')
    ? 'all-stages-done'
    : (stagesRun.length === 0 ? 'already-planned' : 'all-stages-done')
}
return out
```

When the Workflow returns, go to Step 6 and print the summary from the returned object (`reason`, `slug`, `stagesRun`, `stagesSkipped`, `produced`, `failedStage`).

## Step 4 — Stage worker prompts

These are the prompts the pipeline dispatches (embedded in the Step 3 script as `stageWorkerPrompt`, and used verbatim by the Fallback pipeline). Keep the two copies in sync. All stage workers run as `subagent_type: general-purpose` on `model: opus` (the authoring commands are opus-grade synthesis), one at a time.

**Stage worker** (for `<stage>` ∈ prd, research, architect, test, plan):

> You are a `<stage>` worker dispatched by `/pm:autoplan` for project `<slug>`.
>
> Invoke the Skill tool with skill `pm:<stage>` and args `<slug> --auto` (for `prd`, args are `<idea> --auto` — prd creates the slug), and follow that command fully. If the Skill tool is unavailable or `pm:<stage>` is not in your available skills, instead read `${CLAUDE_PLUGIN_ROOT}/commands/<stage>.md` and follow its contents as your instructions, treating `$ARGUMENTS` as `<slug> --auto`.
>
> Rules: run ONLY the `<stage>` stage. Never commit or push. Do not run any other pm command. The `--auto` flag already authorizes best-judgment decisions instead of asking the user — but do NOT improvise past a genuine hard blocker (a missing REQUIRED input); surface it and stop, leaving the artifact unwritten.
>
> When finished, report back ONLY: the stage status, and — for `prd` only — the project slug exactly as written in the created `prd.md` frontmatter. Everything downstream reads from disk.

Never paste PRD, research, or code content into a stage worker prompt beyond slug + idea — the worker reads everything from disk itself. Whatever the worker reports, the orchestrator re-confirms the artifact on disk via the next presence check.

Note (expected, not a bug): the `research` worker, running `pm:research --auto`, will itself dispatch persona subagents in parallel — nested dispatch, exactly as `/pm:auto`'s execute worker may spawn parallel Agent subagents for parallelizable work.

## Step 5 — Stop conditions

The pipeline computes these in code (Step 3 script). It stops and runs Step 6 when any fires:

- **All stages done** — the pipeline reached `plan` and task files are on disk. (`reason: 'all-stages-done'`) Hand off to `/pm:auto <slug>`.
- **Already planned** — resume mode where every stage's artifact already existed (nothing left to author). (`reason: 'already-planned'`) Hand off to `/pm:auto <slug>`.
- **PRD blocked** — the prd stage hit a hard blocker (e.g. no idea seed) and produced no `prd.md`. (`reason: 'prd-blocked'`) Hint: re-run with a one-line idea.
- **Anomaly** — a stage worker ran but its expected artifact is missing on disk (worker died, refused, or the underlying command stopped on a blocker). (`reason: 'anomaly'`, `failedStage` names it.) Surface it; hint: run `/pm:<failedStage> <slug>` supervised to see what it needs.
- **Bad inputs** — the Workflow `args` never populated (passed as an unparseable string, or Step 3.1 skipped). (`reason: 'bad-inputs'`)

## Step 6 — Final summary

Always printed by you (the orchestrator) when the Workflow returns, whatever the stop reason:

```
/pm:autoplan finished — <all stages done | already planned | prd blocked | anomaly at architect | bad inputs>
Slug:        recurring-s3-exports
Stages run:  prd, research, architect, test, plan
Skipped:     —  (or: research (already present))
Produced:    prd.md, goals.md, research/, architecture.md, testing.md, tasks/
Next: /pm:auto <slug>        (execute → verify the generated tasks)
      (on a stop: a stop-reason-appropriate hint — /pm:prd <idea>, /pm:architect <slug>, …)
```

## Fallback pipeline (only when the Workflow tool is unavailable)

Run the pipeline yourself, in this context. **Continuation contract — read this first:** after EVERY stage subagent result your turn is **not** over. Your immediate next action is exactly one of: (a) run the next stage's presence check / dispatch, or (b) print the Step 6 summary because a Step 5 stop condition fired. Ending your turn with stages remaining and no stop condition met is a defect, not a stopping point. Do not narrate or yield between stages; just continue.

Walk the fixed order `prd → research → architect → test → plan`:

1. **Decide skip.** prd: skip in resume mode. research/architect/test/plan: skip if its artifact is already present (from Step 2) and `--force` was not passed. Record skips.
2. **Dispatch ONE Agent subagent** (the matching Step 4 prompt; `subagent_type: general-purpose`, `model: opus`). For prd, args are `<idea> --auto` and you capture the slug from its report. Serial — one stage at a time; parallel dispatch here is a bug.
3. **Disk is truth.** After the worker returns, confirm the stage's artifact on disk:
   - prd → `prd.md` + `<version>/goals.md` exist; read the slug from `prd.md` frontmatter and use it downstream.
   - research → any file under `<version>/research/`.
   - architect → `<version>/architecture.md`.
   - test → `<version>/testing.md`.
   - plan → any file under `<version>/tasks/`.
   Missing after the worker ran → **stop** (anomaly); name the stage. prd producing no slug/`prd.md` → **stop** (prd-blocked).
4. **Report** one status line per stage, then immediately continue:

```
stage prd       — ✓ created project recurring-s3-exports
stage research  — ✓ done
stage architect — ✓ done
stage test      — ✓ done
stage plan      — ✓ done
```

When a stop condition fires (or the pipeline completes), print the Step 6 summary.

## Context isolation guarantees

This command exists to keep state in files, not in context:

- Every stage runs in a **brand-new subagent with a fresh context**. The architect worker has no memory of the research interview; it reads `research/` from disk. That is the plugin's existing file-state contract.
- The control loop holds only the slug, per-stage status lines, and the presence-check booleans — no PRD prose, no research findings, no task content. Even a worker's structured return is advisory; the decision to proceed comes only from the fresh on-disk presence check.

## Output discipline
- Never claim, execute, verify, complete, or release — autoplan is the authoring phase only.
- Never commit or push, and don't let stage workers commit or push.
- `--force` is autoplan's own flag (re-run present stages); it only flips the skip-present decision. Stage workers always get `--auto`, never `--force`.
- Disk is truth: re-confirm each stage's artifact on disk before proceeding; worker reports are advisory.
- Serial dispatch only — concurrent stage workers here are a bug (a stage depends on the prior stage's on-disk output).
- Surface hard blockers verbatim — don't paper over a stage that stopped without writing its artifact.

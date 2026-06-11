---
description: Multi-persona research on a PRD. Orchestrator picks personas from the catalog and dispatches parallel Agent subagents; each writes a findings report.
model: opus
argument-hint: <slug> [--auto]
---

# /pm:research — Multi-persona research

You are running the `/pm:research` command. You are the **orchestrator**. You do NOT do the research yourself — you pick personas, dispatch them as parallel subagents, and assemble the results.

## Inputs
- Slug: `$ARGUMENTS` (use active-project resolution if empty).
- `--auto` (anywhere in `$ARGUMENTS`) — **override mode.** Do not ask the user any questions. At every point where this command would normally interview, confirm, or present an `AskUserQuestion`, instead choose the best option from the PRD / research / architecture / repo signals and your own expertise, state the decision and a one-line rationale inline, and continue. Reserve stopping for hard blockers only (a missing REQUIRED input that cannot be inferred). When a gate would replace an existing artifact, take the **overwrite-with-backup** path automatically (back up / archive first — never lose data). Default (flag absent) = the interactive behavior described below.

## Step 1 — Resolve project and active version

Active-project resolution:
1. If `$ARGUMENTS` names a `.pm/<slug>/` that exists, use it.
2. Else if exactly one `.pm/<slug>/` exists, use that one and tell the user.
3. Else if exactly one project has `status: active`, use that.
4. Else list slugs and ask.

Read `prd.md` frontmatter for `active_version` (default: `v1`). All research goes into `.pm/<slug>/<active_version>/research/`.

If `.pm/<slug>/<active_version>/research/` already contains files, ask the user whether to:
- **Replace** existing research (archive current research/ to research-old-<timestamp>/ first),
- **Add to** existing research (only run new personas),
- **Cancel**.

Under `--auto`, take **Replace** automatically — archive the current `research/` to `research-old-<timestamp>/` first (overwrite-with-backup), then proceed.

## Step 2 — Read the PRD and version goals

Read:
- `.pm/<slug>/prd.md` (full file)
- `.pm/<slug>/<active_version>/goals.md` (full file)
- `${CLAUDE_PROJECT_DIR}/plugins/pm/personas.md` (the catalog — adjust path if running outside this repo; the plugin's own personas.md ships with the plugin)

If `prd.md` is missing, stop and tell the user to run `/pm:prd` first.

## Step 3 — Detect repo state (greenfield vs brownfield)

Check the working directory for substantial existing code. Signals:
- Non-empty `src/`, `lib/`, `app/`, or top-level source files (.py, .ts, .java, .go, .rs, etc.)
- Presence of package.json, pom.xml, Cargo.toml, go.mod, requirements.txt, pyproject.toml, etc.
- More than ~10 source files outside `.pm/`, `.claude/`, `.git/`, `node_modules/`, etc.

If brownfield → you MUST include the `existing-codebase-archaeologist` persona.

## Step 4 — Pick personas

Based on PRD + goals + repo state, pick 3–6 personas from the catalog (and optionally instantiate ad-hoc ones for unusual domains). For each pick, write a one-sentence justification.

Present the picks to the user with AskUserQuestion (multiSelect) — they can deselect any persona, and they can add personas via the "Other" option. Default selection = your full picks. Under `--auto`, skip the AskUserQuestion and dispatch your full set of picked personas as-is.

## Step 5 — Dispatch in parallel

For each selected persona, spawn an **Agent** call (`subagent_type: general-purpose`, `model: sonnet`) IN PARALLEL — issue all Agent tool calls in a single response, not one at a time. The orchestrator (this command) runs on Opus for synthesis; personas run on Sonnet because each writes a focused ~800-word report well within Sonnet's strength, and dispatching 3–6 in parallel makes the cost difference significant.

Each agent prompt MUST include:
- The persona display name and brief (copy verbatim from `personas.md`, or use the ad-hoc framing for instantiated personas).
- The full text of `prd.md`.
- The full text of `<active_version>/goals.md`.
- The repo root path and instructions to read existing code when relevant.
- The exact output template from `personas.md` ("Each persona writes a single markdown report to ...").
- The exact file path the persona must write to: `.pm/<slug>/<active_version>/research/<persona-slug>.md`.
- An instruction to reference PRD/goals sections in EVERY finding (e.g. `[prd.md §3.2]`, `[goals.md §Acceptance bar]`).
- Length cap: ~800 words. Quality over volume.

Example dispatch prompt skeleton for one persona:

> You are the **security-architect** persona for the `<slug>` project research phase.
>
> **Your brief:** <verbatim from personas.md catalog>
>
> **Your task:** Read the PRD and v1 goals below, plus any relevant existing code in `<repo path>`. Produce a research report at `.pm/<slug>/v1/research/security-architect.md` using the structure in personas.md (Summary, Findings, Gotchas, Recommendations, Open questions for the user, Out of scope). Reference PRD/goals sections in every finding. ~800 words max.
>
> **PRD:**
> <full prd.md>
>
> **v1 goals:**
> <full goals.md>
>
> Write the file to the path above and return a one-paragraph summary of your top findings.

## Step 6 — Assemble

After all agents return, write `.pm/<slug>/<active_version>/research/_index.md`:

```markdown
# Research index — <slug> <active_version>

Generated: <YYYY-MM-DD>

## Personas run
- [<persona-slug>](<persona-slug>.md) — <one-line headline>
- ...

## Cross-cutting open questions
Collect every "Open questions for the user" item from all reports here, deduplicated. Each links back to its source report.

## Recommended next step
- If there are unresolved open questions that materially affect scope: ask the user to answer them, then suggest `/pm:amend <slug>` if the answers change the PRD.
- Otherwise: `/pm:plan <slug>`.
```

## Step 7 — Surface open questions

If the assembled index has open questions, present them to the user. Group by report. Ask which (if any) they want to answer now. For each answered question:
- Update the relevant research report by appending an `## Update — <date>` section that captures the user's answer and any revised recommendation.
- If the answer materially changes scope, suggest `/pm:amend <slug>` next.

Under `--auto`, do not run the answer-now loop. The open questions are already captured in `_index.md` (Step 6), so nothing is lost — leave them for the user to address later and continue to hand-off.

## Step 8 — Hand off

Print:
- Count of reports written and the index path.
- Outstanding open questions count.
- Next-step hint: `/pm:plan <slug>`.

## Output discipline
- Subagent calls go in a SINGLE response, parallel. Sequential is a bug.
- If a subagent fails or returns nothing, surface it to the user — don't silently drop the persona.
- Don't summarize what each persona said in your final message. The user reads the files; you just orient them.

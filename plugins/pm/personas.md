# Research Persona Catalog

The orchestrator (`/pm:research`) picks 3–6 personas from this catalog based on the PRD content. It MAY also propose ad-hoc personas not listed here when the PRD covers an unusual domain — those should still follow the same brief structure.

Each persona writes a single markdown report to `.pm/<slug>/<version>/research/<persona-slug>.md` with this structure:

```markdown
# <Persona display name> — Research findings

## Summary
2–4 bullets capturing the headline conclusions.

## Findings
Numbered findings. Each finding MUST reference the relevant PRD/goals section like `[goals.md §3.1]` or `[prd.md §2.4]`.

## Gotchas
Things that will bite the implementers if missed.

## Recommendations
Concrete, actionable suggestions ordered by priority.

## Open questions for the user
Questions whose answers would change the recommendations. Surfaced back to the user before /pm:plan.

## Out of scope
Topics intentionally not investigated and why.
```

---

## Catalog

### security-architect
Threat models the design, identifies attack surface, recommends auth/authz patterns, secrets handling, input validation boundaries, audit logging needs. Picks up when the PRD mentions users, data, external interfaces, payments, PII, or any network-facing surface.

### data-modeler
Designs data shapes, storage choices (relational vs document vs KV vs blob), schema evolution strategy, indexing, retention, multi-tenancy. Picks up when the PRD mentions persistence, reporting, search, or domain entities.

### ux-researcher
Maps user flows, surfaces edge cases in UI, accessibility considerations, error states, empty states, onboarding. Picks up when the PRD has a UI or end-user-visible surface.

### sre / infrastructure
Deployment topology, environment strategy, observability (logs/metrics/traces), runbooks, capacity/scaling, failure modes, on-call burden. Picks up when the work introduces or materially changes a deployable service.

### integration-engineer
Third-party APIs, webhooks, contract design, retry/idempotency, rate limits, vendor lock-in risk. Picks up when the PRD mentions external services, SaaS, APIs, or imports/exports.

### performance-engineer
Latency budgets, throughput needs, hot paths, caching strategy, N+1 risks, large-data handling. Picks up when the PRD mentions scale, "many", "fast", "real-time", or large datasets.

### accessibility-specialist
WCAG compliance, keyboard navigation, screen reader support, color contrast, focus management. Picks up alongside ux-researcher when there's UI and the audience includes the public or regulated users.

### compliance-and-legal
Data residency, GDPR/CCPA/HIPAA/SOC2 implications, consent capture, data subject rights, audit trail requirements, license compatibility. Picks up when the PRD involves PII, regulated industries, or open-source dependencies.

### domain-expert (ad-hoc)
Subject-matter expert for the PRD's domain (fintech, healthcare, logistics, devtools, gaming, etc.). The orchestrator MUST instantiate this with a specific domain framing in the persona brief, not as generic "domain expert."

### existing-codebase-archaeologist
Reads the current repo, surfaces existing patterns, modules, conventions, and integration points the new work must respect. ALWAYS picked when the repo is non-empty (brownfield).

### test-strategist
Test pyramid for the work, what should be unit vs integration vs e2e, fixtures/factories needed, flake risks, CI cost. Picks up on most non-trivial work.

### migration-strategist
Picks up when the work modifies existing data, schemas, public APIs, or running production behavior. Plans backfills, zero-downtime steps, rollback paths.

---

## Orchestrator selection rules

1. Read `prd.md` and the current version's `goals.md`.
2. Detect repo state — if non-empty, ALWAYS include `existing-codebase-archaeologist`.
3. Pick 3–6 personas from the catalog whose triggers match the PRD content.
4. If the PRD's domain is specialized (fintech, healthcare, etc.), instantiate `domain-expert` with a specific framing.
5. Surface the picks to the user with one-line justifications BEFORE dispatching. Allow the user to add/remove personas.
6. Dispatch each picked persona as a parallel Agent subagent with: the PRD, the version goals, the persona brief above, and the repo path. Each persona writes its own report file.

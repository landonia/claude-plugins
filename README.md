# claude-plugins

Personal Claude Code plugin marketplace.

## Add this marketplace

In Claude Code, run:
```
/plugin marketplace add landonia/claude-plugins
```

## Available plugins

### interaction-logger
Logs every Claude Code prompt and response to `~/.claude/interaction_history.jsonl`.

**Install:**
```
/plugin install interaction-logger@landonia-plugins
```

### java-guidelines
Injects Java coding patterns, conventions, and best practices (naming, design patterns, package structure, testing, logging, etc.) into the agent context whenever Java code is being written or reviewed.

**Install:**
```
/plugin install java-guidelines@landonia-plugins
```

### pm
Project management pipeline for large/complex work: PRD interview, multi-persona research, architecture & tech-stack decisioning (`/pm:architect`), ordered task generation, stack-aware execution, independent verification, and PR submission. Supports versioned milestones (v1, v2, ...), multi-developer team workflow with branch-per-task (`/pm:claim`, `/pm:complete`, `/pm:resume`), and optional Jira integration (auto status sync via `acli` — opt in per project with `/pm:jira-init`). Uses per-command model selection (Opus for reasoning, Sonnet for execution, Haiku for read-only) for cost-efficient operation. Twenty slash commands under the `/pm:` namespace.

[Plugin README](plugins/pm/README.md)

**Install:**
```
/plugin install pm@landonia-plugins
```

## Releasing

Each plugin has its own version, changelog, tag, and GitHub release. Versioning is automated by [release-please](https://github.com/googleapis/release-please) — you don't bump `plugin.json` by hand.

### Commit format

Use [Conventional Commits](https://www.conventionalcommits.org/) with the plugin folder name as the scope:

```
feat(pm): add /pm:architect step
fix(java-guidelines): correct Spring Boot version
docs(interaction-logger): clarify log format
chore: update CI
```

Bump rules:

| Commit prefix | Effect |
|---|---|
| `feat(<plugin>): ...` | minor bump for that plugin |
| `fix(<plugin>): ...` | patch bump for that plugin |
| `feat(<plugin>)!: ...` or `BREAKING CHANGE:` footer | major bump |
| `docs:` / `chore:` / `refactor:` / `test:` / `build:` / `ci:` | no version bump |

Top-level changes (root README, marketplace.json, etc.) use `chore:` / `docs:` without a plugin scope and don't bump any plugin — that's intentional.

### How a release happens

1. Push a `feat(...)` or `fix(...)` commit to `main`.
2. The release-please workflow opens (or updates) a release PR titled `chore: release ...` that bumps the affected plugin's `plugin.json`, appends a `CHANGELOG.md` entry, and updates `.release-please-manifest.json`.
3. Review the PR; merge when ready.
4. The merge triggers release-please to tag the affected plugin(s) (e.g. `pm-v1.1.0`) and create a GitHub release with the changelog as the body.

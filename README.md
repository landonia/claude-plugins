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


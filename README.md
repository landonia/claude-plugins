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
Project management pipeline for large/complex work: PRD interview, multi-persona research, ordered task generation, stack-aware execution, independent verification, and PR submission. Supports versioned milestones (v1, v2, ...) and multi-developer team workflow with branch-per-task and `/pm:claim` / `/pm:complete` / `/pm:resume`. Fifteen slash commands under the `/pm:` namespace.

[Plugin README](plugins/pm/README.md)

**Install:**
```
/plugin install pm@landonia-plugins
```


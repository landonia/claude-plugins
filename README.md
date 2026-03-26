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

If hooks do not register automatically, run the install script from your project directory as a fallback:
```bash
bash /path/to/claude-plugins/scripts/install-plugin.sh interaction-logger
```

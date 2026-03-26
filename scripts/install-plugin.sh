#!/usr/bin/env bash
# scripts/install-plugin.sh
#
# Installs a plugin from this marketplace and registers its hooks in settings.json.
# Claude Code's built-in /plugin install handles skills but does not process hooks.json —
# this script fills that gap.
#
# Usage (run from your project directory):
#   bash /path/to/claude-plugins/scripts/install-plugin.sh <plugin-name> [--global]
#
# Examples:
#   bash scripts/install-plugin.sh interaction-logger
#   bash scripts/install-plugin.sh interaction-logger --global
#
# Options:
#   --global   Register hooks in global settings (~/.claude/settings.json)
#              instead of the current project's .claude/settings.json

set -euo pipefail

PLUGIN_SPEC="${1:-}"
GLOBAL=false
for arg in "${@:2}"; do
  [[ "$arg" == "--global" ]] && GLOBAL=true
done

if [[ -z "$PLUGIN_SPEC" ]]; then
  echo "Usage: $0 <plugin-name> [--global]"
  echo "Example: $0 interaction-logger"
  exit 1
fi

# Strip marketplace suffix if present (e.g. "interaction-logger@landonia-plugins" -> "interaction-logger")
PLUGIN_NAME="${PLUGIN_SPEC%%@*}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE_ROOT="$(dirname "$SCRIPT_DIR")"
CLAUDE_CONFIG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
MARKETPLACE_JSON="$MARKETPLACE_ROOT/.claude-plugin/marketplace.json"

if [[ ! -f "$MARKETPLACE_JSON" ]]; then
  echo "Error: marketplace.json not found at $MARKETPLACE_JSON"
  exit 1
fi

# Resolve plugin subdirectory from marketplace catalog
PLUGIN_SUBPATH=$(python3 - "$MARKETPLACE_JSON" "$PLUGIN_NAME" <<'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    m = json.load(f)
for p in m.get('plugins', []):
    if p['name'] == sys.argv[2]:
        print(p['source']['path'].lstrip('./'))
        sys.exit(0)
print(f"Plugin '{sys.argv[2]}' not found in marketplace", file=sys.stderr)
sys.exit(1)
PYEOF
) || exit 1

PLUGIN_ROOT="$MARKETPLACE_ROOT/$PLUGIN_SUBPATH"

if [[ ! -d "$PLUGIN_ROOT" ]]; then
  echo "Error: plugin directory not found at $PLUGIN_ROOT"
  exit 1
fi

HOOKS_JSON="$PLUGIN_ROOT/hooks/hooks.json"

if [[ ! -f "$HOOKS_JSON" ]]; then
  echo "Plugin '$PLUGIN_NAME' has no hooks.json — nothing to register."
  exit 0
fi

# Ensure hook scripts are executable
find "$PLUGIN_ROOT/hooks" -name "*.sh" -exec chmod +x {} \;

# Determine target settings file
if [[ "$GLOBAL" == "true" ]]; then
  SETTINGS_FILE="$CLAUDE_CONFIG/settings.json"
else
  SETTINGS_FILE="$(pwd)/.claude/settings.json"
fi

# Inject hooks into settings.json, expanding ${CLAUDE_PLUGIN_ROOT}
python3 - "$HOOKS_JSON" "$SETTINGS_FILE" "$PLUGIN_ROOT" <<'PYEOF'
import json, os, sys

hooks_file, settings_file, plugin_root = sys.argv[1], sys.argv[2], sys.argv[3]

with open(hooks_file) as f:
    plugin_hooks = json.load(f).get('hooks', {})

settings = {}
if os.path.exists(settings_file):
    with open(settings_file) as f:
        settings = json.load(f)

if 'hooks' not in settings:
    settings['hooks'] = {}

added = []
for event, hook_groups in plugin_hooks.items():
    if event not in settings['hooks']:
        settings['hooks'][event] = []
    for group in hook_groups:
        expanded = json.loads(
            json.dumps(group).replace('${CLAUDE_PLUGIN_ROOT}', plugin_root)
        )
        if expanded not in settings['hooks'][event]:
            settings['hooks'][event].append(expanded)
            cmds = [h.get('command', '') for h in expanded.get('hooks', [])]
            added.append(f"  {event}: {', '.join(cmds)}")

os.makedirs(os.path.dirname(os.path.abspath(settings_file)), exist_ok=True)
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')

if added:
    print(f"Registered hooks in {settings_file}:")
    for line in added:
        print(line)
else:
    print(f"Hooks already registered in {settings_file} — no changes made.")
PYEOF

echo "Plugin '$PLUGIN_NAME' installed successfully."

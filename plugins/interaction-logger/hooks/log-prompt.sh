#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null)
CWD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null)

if [ -n "$PROMPT" ] && [ -n "$CWD" ]; then
  cd "$CWD" && python3 "${CLAUDE_PLUGIN_ROOT}/skills/interaction-logger/scripts/log_interaction.py" \
    --role user --content "$PROMPT" 2>/dev/null
fi
exit 0

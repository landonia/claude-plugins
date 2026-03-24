#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)
if [ -n "$PROMPT" ]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/interaction-logger/scripts/log_interaction.py" \
    --role user --content "$PROMPT" 2>/dev/null
fi
exit 0

#!/bin/bash
INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null)
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  RESPONSE=$(python3 -c "
import json
entries = []
with open('$TRANSCRIPT') as f:
    for line in f:
        line = line.strip()
        if line:
            try: entries.append(json.loads(line))
            except: pass
for entry in reversed(entries):
    if entry.get('type') == 'assistant':
        parts = entry.get('message', {}).get('content', [])
        text = ' '.join(p.get('text','') for p in parts if isinstance(p,dict) and p.get('type')=='text')
        if text:
            print(text)
            break
" 2>/dev/null)
  if [ -n "$RESPONSE" ]; then
    python3 "${CLAUDE_PLUGIN_ROOT}/skills/interaction-logger/scripts/log_interaction.py" \
      --role assistant --content "$RESPONSE" 2>/dev/null
  fi
fi
exit 0

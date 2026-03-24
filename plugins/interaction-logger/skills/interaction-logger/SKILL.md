---
name: interaction-logger
description: >
  Automatically log every user prompt and Claude response to a persistent history file with timestamps and metadata.
  Use this skill whenever the user asks to log interactions, track conversation history, record prompts and outputs,
  audit what decisions led to a result, or review past Claude sessions. Also trigger proactively at the START of
  every session to initialize the log, and at the END of every response to append the interaction. If the user
  says "log this", "add to history", "record this interaction", "what led to this output", or similar — use this skill.
---

# Interaction Logger Skill

Log every prompt and Claude response to a persistent, human-readable history file so you can trace which inputs led to which outputs.

---

## When to use

- **Start of every session**: Initialize the log (check if log file exists; create if not).
- **End of every response**: Append the just-completed interaction.
- **Explicit log requests**: User says "log this", "save this interaction", "add to history".
- **Audit requests**: User asks "what prompt led to this?" or "show me my interaction history".

---

## Log file location

Default: `~/.claude/interaction_history.jsonl`

The user may override this by setting `CLAUDE_INTERACTION_LOG` in their environment or by mentioning a different path. Always respect their preference.

Use `.jsonl` (JSON Lines) — one JSON object per line. This makes it easy to grep, stream, and parse.

---

## Log entry format

Each line in the log file is a JSON object:

```json
{
  "id": "uuid-v4",
  "timestamp": "2026-03-24T14:32:01.123Z",
  "session_id": "short-random-id",
  "sequence": 1,
  "role": "user",
  "content": "The raw text of the prompt",
  "context": {
    "cwd": "/path/to/working/directory",
    "tool": "claude-code"
  }
}
```

Followed immediately by the assistant's response entry:

```json
{
  "id": "uuid-v4",
  "timestamp": "2026-03-24T14:32:05.456Z",
  "session_id": "short-random-id",
  "sequence": 2,
  "role": "assistant",
  "content": "The raw text of the response",
  "context": {
    "cwd": "/path/to/working/directory",
    "tool": "claude-code"
  }
}
```

---

## Implementation: use the logger script

Run the logger script (see `scripts/log_interaction.py`) to append entries. This handles:
- File creation and directory setup
- Session ID generation/reuse (stored in `~/.claude/.current_session`)
- Sequence numbering within a session
- Safe concurrent writes (file locking)
- UTF-8 encoding

### Append a user prompt:
```bash
python3 ~/.claude/skills/interaction-logger/scripts/log_interaction.py \
  --role user \
  --content "The user's prompt text here"
```

### Append an assistant response:
```bash
python3 ~/.claude/skills/interaction-logger/scripts/log_interaction.py \
  --role assistant \
  --content "Claude's response text here"
```

### Start a new session explicitly:
```bash
python3 ~/.claude/skills/interaction-logger/scripts/log_interaction.py \
  --new-session
```

### View recent interactions:
```bash
python3 ~/.claude/skills/interaction-logger/scripts/log_interaction.py \
  --view --last 20
```

### Search history:
```bash
python3 ~/.claude/skills/interaction-logger/scripts/log_interaction.py \
  --search "keyword or phrase"
```

---

## Workflow per interaction

1. **User sends a prompt** → immediately log it with `--role user`
2. **Claude produces a response** → log it with `--role assistant`
3. Both entries share the same `session_id` and auto-increment `sequence`

This creates a paired, traceable record: for any output you're curious about, find its `id`, look at the entry immediately before it (same session, sequence - 1) to see exactly what prompt produced it.

---

## Viewing and querying the log

For quick viewing, run the `--view` command above.

For power users, the `.jsonl` format works natively with tools like:
- `jq` — e.g. `cat ~/.claude/interaction_history.jsonl | jq 'select(.role=="user") | .content'`
- `grep` — `grep "keyword" ~/.claude/interaction_history.jsonl`
- Any JSON lines reader

---

## Session management

- A **session** groups all interactions in one logical work block (e.g., one Claude Code session).
- Session ID is a short random string stored in `~/.claude/.current_session`.
- New session = delete or rotate `.current_session` file, or use `--new-session` flag.
- The session file is reset automatically when a new terminal session starts (the script checks file age: if `.current_session` is older than 8 hours, it auto-rotates).

---

## Privacy note

The log file contains your raw prompts and responses in plaintext. It is stored locally at `~/.claude/interaction_history.jsonl` and never sent anywhere. You are responsible for protecting this file.

---

## Setup (first time)

If the script isn't installed yet, Claude should copy it from the skill bundle:

```bash
mkdir -p ~/.claude/skills/interaction-logger/scripts
cp <skill_bundle_path>/scripts/log_interaction.py ~/.claude/skills/interaction-logger/scripts/
chmod +x ~/.claude/skills/interaction-logger/scripts/log_interaction.py
```

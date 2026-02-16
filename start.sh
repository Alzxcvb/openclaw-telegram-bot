#!/bin/bash
MODEL="${OPENCLAW_MODEL:-google/gemma-3n-e2b-it:free}"
CONFIG="{\"agents\":{\"defaults\":{\"model\":{\"primary\":\"$MODEL\"}}},\"channels\":{\"telegram\":{\"enabled\":true,\"dmPolicy\":\"open\",\"allowFrom\":[\"*\"],\"streamMode\":\"partial\"}},\"gateway\":{\"bind\":\"lan\"}}"

# Write config to every possible location
mkdir -p "$HOME/.openclaw"
mkdir -p /tmp/openclaw-state
mkdir -p /home/node/.openclaw 2>/dev/null

echo "$CONFIG" > "$HOME/.openclaw/openclaw.json"
echo "$CONFIG" > /tmp/openclaw-state/openclaw.json 2>/dev/null
echo "$CONFIG" > /home/node/.openclaw/openclaw.json 2>/dev/null

# Also remove any backup that might be restored
rm -f "$HOME/.openclaw/openclaw.json.bak" 2>/dev/null
rm -f /home/node/.openclaw/openclaw.json.bak 2>/dev/null

export OPENCLAW_DEFAULT_MODEL="$MODEL"

exec node openclaw.mjs gateway --allow-unconfigured --bind lan

#!/bin/bash
MODEL="${OPENCLAW_MODEL:-google/gemma-3n-e2b-it:free}"

# Debug: find all config files in the image
echo "=== Finding all openclaw config files ==="
find / -name "openclaw.json" -o -name "openclaw.json5" -o -name "config.json" 2>/dev/null | head -20
echo "=== Checking default config content ==="
for f in $(find / -name "openclaw.json" 2>/dev/null); do
  echo "--- $f ---"
  cat "$f" 2>/dev/null | head -5
done

# Write our config
CONFIG="{\"agents\":{\"defaults\":{\"model\":{\"primary\":\"$MODEL\"}}},\"channels\":{\"telegram\":{\"enabled\":true,\"dmPolicy\":\"open\",\"allowFrom\":[\"*\"],\"streamMode\":\"partial\"}},\"gateway\":{\"bind\":\"lan\"}}"
mkdir -p "$HOME/.openclaw"
echo "$CONFIG" > "$HOME/.openclaw/openclaw.json"

# Overwrite any built-in configs we find
for f in $(find / -name "openclaw.json" 2>/dev/null); do
  echo "$CONFIG" > "$f" 2>/dev/null
done

exec node openclaw.mjs gateway --allow-unconfigured --bind lan

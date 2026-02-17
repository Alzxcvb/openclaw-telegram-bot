#!/bin/bash
mkdir -p "$HOME/.openclaw"

# Set dummy Brave API key so OpenClaw enables web_search tool
export BRAVE_API_KEY=dummy

# Start brave_shim (DuckDuckGo proxy) in the background
python3 /opt/brave_shim/brave_shim.py &

# Brief wait for shim startup
sleep 3

# Use OpenClaw's own CLI to set the model (respects internal config format)
node openclaw.mjs config set agents.defaults.model.primary "openrouter/google/gemini-2.0-flash-001" 2>&1 || true
node openclaw.mjs config set channels.telegram.enabled true 2>&1 || true
node openclaw.mjs config set channels.telegram.dmPolicy open 2>&1 || true
node openclaw.mjs config set gateway.bind lan 2>&1 || true

exec node openclaw.mjs gateway --allow-unconfigured --bind lan

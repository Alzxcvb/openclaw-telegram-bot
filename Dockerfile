FROM ghcr.io/openclaw/openclaw:latest

ENV NODE_ENV=production

# Install Python 3 and pip for the brave_shim service
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip curl && \
    rm -rf /var/lib/apt/lists/* && \
    python3 -m pip install --break-system-packages fastapi uvicorn duckduckgo-search pyyaml

# Copy brave_shim into the image
COPY brave_shim/ /opt/brave_shim/

# Patch OpenClaw's Brave Search URL to point to local shim
RUN find /app -type f \( -name '*.mjs' -o -name '*.js' -o -name '*.cjs' \) | \
    xargs grep -l 'api.search.brave.com' 2>/dev/null | \
    xargs -I{} sed -i 's|https://api.search.brave.com|http://127.0.0.1:8000|g' {} || true

# Bake config into the image at the default config path
RUN mkdir -p /home/node/.openclaw
COPY --chown=node:node openclaw-config.json /home/node/.openclaw/openclaw.json

# Switch back to node user
USER node

COPY --chmod=755 start.sh /tmp/start.sh

ENTRYPOINT ["/bin/bash", "/tmp/start.sh"]
CMD []

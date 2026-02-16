FROM ghcr.io/openclaw/openclaw:latest

ENV NODE_ENV=production

ARG CACHEBUST=1
RUN mkdir -p /root/.openclaw && \
    echo '{"agents":{"defaults":{"model":{"primary":"anthropic/claude-sonnet-4-5-20250929"}}},"channels":{"telegram":{"enabled":true,"dmPolicy":"open","allowFrom":["*"],"streamMode":"partial"}},"gateway":{"bind":"lan"}}' > /root/.openclaw/openclaw.json

CMD ["node", "openclaw.mjs", "gateway", "--allow-unconfigured", "--bind", "lan"]

FROM ghcr.io/openclaw/openclaw:latest

ENV NODE_ENV=production

ARG CACHEBUST=1
RUN mkdir -p $HOME/.openclaw && \
    echo '{"agents":{"defaults":{"model":{"primary":"deepseek/deepseek-r1-0528:free"}}},"channels":{"telegram":{"enabled":true,"dmPolicy":"open","allowFrom":["*"],"streamMode":"partial"}},"gateway":{"bind":"lan"}}' > $HOME/.openclaw/openclaw.json

CMD ["node", "openclaw.mjs", "gateway", "--allow-unconfigured", "--bind", "lan"]

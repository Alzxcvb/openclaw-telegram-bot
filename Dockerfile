FROM ghcr.io/openclaw/openclaw:latest

ENV NODE_ENV=production

COPY --chmod=755 start.sh /tmp/start.sh

ENTRYPOINT ["/bin/bash", "/tmp/start.sh"]
CMD []

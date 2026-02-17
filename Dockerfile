FROM ghcr.io/openclaw/openclaw:latest

ENV NODE_ENV=production

# Keep root for entrypoint so start.sh can fix config permissions
USER root
COPY --chmod=755 start.sh /tmp/start.sh

ENTRYPOINT ["/bin/bash", "/tmp/start.sh"]
CMD []

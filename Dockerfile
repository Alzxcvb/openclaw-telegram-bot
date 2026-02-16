FROM ghcr.io/openclaw/openclaw:latest

ENV NODE_ENV=production

COPY start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/bin/bash", "/start.sh"]
CMD []

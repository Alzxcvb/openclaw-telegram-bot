FROM ghcr.io/openclaw/openclaw:latest

ENV NODE_ENV=production

COPY start.sh /start.sh

CMD ["/bin/bash", "/start.sh"]

FROM ghcr.io/openclaw/openclaw:latest

ENV NODE_ENV=production

# Keep root for entrypoint so start.sh can fix config permissions
USER root
COPY --chmod=755 start.sh /tmp/start.sh
COPY morning-brief/ /app/morning-brief/
COPY skills/ /app/skills/

# Install pip and Python dependencies at build time
RUN apt-get update -qq && apt-get install -y -qq python3-pip && \
    pip3 install --quiet -r /app/morning-brief/requirements.txt

ENTRYPOINT ["/bin/bash", "/tmp/start.sh"]
CMD []

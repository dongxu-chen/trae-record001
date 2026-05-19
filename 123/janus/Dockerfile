FROM canyanio/janus-gateway:latest

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/local/share/janus/recordings && \
    mkdir -p /var/log/janus && \
    chmod -R 777 /usr/local/share/janus/recordings && \
    chmod -R 777 /var/log/janus

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8088/janus/info || exit 1

CMD ["janus"]

FROM golang:1.21-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    llvm \
    libbpf-dev \
    linux-headers-amd64 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN go install github.com/cilium/ebpf/cmd/bpf2go@latest

COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . .

RUN make generate-bpf || true
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags "-s -w" -o escape-detector ./cmd/escape-detector

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    iproute2 \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/escape-detector /usr/local/bin/
COPY --from=builder /app/configs /etc/escape-detector

RUN mkdir -p /var/lib/escape-detector /var/log/escape-detector

EXPOSE 9090

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

CMD ["escape-detector", "--config", "/etc/escape-detector/config.yaml"]

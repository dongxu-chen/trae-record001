FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o k8s-auditor ./cmd/auditor

FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

COPY --from=builder /app/k8s-auditor /usr/local/bin/
COPY config.yaml /app/config.yaml

RUN mkdir -p /app/reports

ENTRYPOINT ["k8s-auditor"]

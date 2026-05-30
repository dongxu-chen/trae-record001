FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum* ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o kafka-lag-analyzer ./cmd/analyzer

FROM alpine:3.19

RUN apk add --no-cache ca-certificates tzdata

WORKDIR /app

COPY --from=builder /app/kafka-lag-analyzer .
COPY config.yaml .

EXPOSE 8080

ENTRYPOINT ["/app/kafka-lag-analyzer"]
CMD ["--config", "/app/config.yaml"]

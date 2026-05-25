FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /app/db-bench ./cmd/benchmark

FROM alpine:3.19

RUN apk add --no-cache ca-certificates tzdata

WORKDIR /app

COPY --from=builder /app/db-bench /app/db-bench
COPY --from=builder /app/configs /app/configs

EXPOSE 9091

ENTRYPOINT ["/app/db-bench"]
CMD ["--help"]

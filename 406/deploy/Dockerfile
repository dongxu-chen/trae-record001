FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o health-check ./cmd/server/

FROM alpine:latest
RUN apk --no-cache add ca-certificates

WORKDIR /root/

COPY --from=builder /app/health-check .
COPY --from=builder /app/configs ./configs

EXPOSE 8080 8081 9090

CMD ["./health-check", "--config", "configs/config.yaml"]

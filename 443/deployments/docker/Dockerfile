FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /cross-cloud-lb ./cmd/main.go

FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

COPY --from=builder /cross-cloud-lb /app/cross-cloud-lb
COPY config.yaml /app/config.yaml

EXPOSE 18000 9090

ENTRYPOINT ["/app/cross-cloud-lb"]
CMD ["--config", "/app/config.yaml"]

FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o kafka-mirror ./cmd/main.go

FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

COPY --from=builder /app/kafka-mirror .
COPY config/config.yaml ./config/config.yaml

EXPOSE 9090

CMD ["./kafka-mirror", "-config", "./config/config.yaml"]

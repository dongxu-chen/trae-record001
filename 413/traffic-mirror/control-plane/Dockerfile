FROM golang:1.21-alpine AS builder

RUN apk add --no-cache git gcc musl-dev

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=1 GOOS=linux go build -o /control-plane ./cmd/server/

FROM alpine:3.19

RUN apk add --no-cache ca-certificates

COPY --from=builder /control-plane /usr/local/bin/control-plane

EXPOSE 8080 18000

ENTRYPOINT ["/usr/local/bin/control-plane"]

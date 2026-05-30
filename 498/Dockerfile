FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /downsampler ./cmd/downsampler

FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

COPY --from=builder /downsampler /usr/local/bin/downsampler
COPY configs/config.yaml /app/configs/config.yaml

EXPOSE 9091

ENTRYPOINT ["/usr/local/bin/downsampler"]
CMD ["--config", "/app/configs/config.yaml"]

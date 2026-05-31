module clickhouse-rate-limiter

go 1.26.3

require (
	github.com/ClickHouse/clickhouse-go v1.5.4
	github.com/google/uuid v1.6.0
	github.com/gorilla/mux v1.8.1
	golang.org/x/time v0.15.0
)

require github.com/cloudflare/golz4 v0.0.0-20150217214814-ef862a3cdc58 // indirect

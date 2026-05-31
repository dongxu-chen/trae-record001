@echo off
echo Starting Elasticsearch Shard Balancer Backend...
cd backend
go mod download
go run cmd/main.go
pause

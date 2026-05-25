.PHONY: all build test clean deps run run-mysql run-postgres run-mongo docker-up docker-down

APP_NAME := db-bench
CMD_DIR := ./cmd/benchmark
OUTPUT_DIR := ./bin

all: build

deps:
	go mod download
	go mod tidy

build:
	@mkdir -p $(OUTPUT_DIR)
	CGO_ENABLED=0 go build -ldflags="-s -w" -o $(OUTPUT_DIR)/$(APP_NAME) $(CMD_DIR)

build-linux:
	@mkdir -p $(OUTPUT_DIR)
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o $(OUTPUT_DIR)/$(APP_NAME)-linux-amd64 $(CMD_DIR)

build-windows:
	@mkdir -p $(OUTPUT_DIR)
	CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o $(OUTPUT_DIR)/$(APP_NAME)-windows-amd64.exe $(CMD_DIR)

test:
	go test -v ./...

clean:
	rm -rf $(OUTPUT_DIR)

run: build
	@echo "Usage: make run -- --db-type mysql --db-host localhost ..."
	@echo "   or: make run-mysql / run-postgres / run-mongo"

run-mysql: build
	$(OUTPUT_DIR)/$(APP_NAME) -c configs/config.yaml

run-postgres: build
	$(OUTPUT_DIR)/$(APP_NAME) -c configs/config-postgres.yaml

run-mongo: build
	$(OUTPUT_DIR)/$(APP_NAME) -c configs/config-mongodb.yaml

docker-up:
	cd deployments && docker-compose up -d

docker-down:
	cd deployments && docker-compose down

docker-logs:
	cd deployments && docker-compose logs -f

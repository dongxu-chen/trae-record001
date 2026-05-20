.PHONY: all build clean test run deps

APP_NAME := backupd
VERSION := 1.0.0
BUILD_DIR := build

all: build

deps:
	@echo "Downloading dependencies..."
	@go mod download
	@go mod tidy

build: deps
	@echo "Building $(APP_NAME) v$(VERSION)..."
	@mkdir -p $(BUILD_DIR)
	@go build -ldflags "-X main.Version=$(VERSION)" -o $(BUILD_DIR)/$(APP_NAME) ./cmd/backupd
	@echo "Build completed: $(BUILD_DIR)/$(APP_NAME)"

test:
	@echo "Running tests..."
	@go test -v ./...

run: build
	@echo "Running $(APP_NAME)..."
	@./$(BUILD_DIR)/$(APP_NAME) -config config.yaml

run-once: build
	@echo "Running $(APP_NAME) once..."
	@./$(BUILD_DIR)/$(APP_NAME) -config config.yaml -once

clean:
	@echo "Cleaning up..."
	@rm -rf $(BUILD_DIR)
	@rm -rf backups
	@echo "Clean completed"

install: build
	@echo "Installing $(APP_NAME) to /usr/local/bin..."
	@cp $(BUILD_DIR)/$(APP_NAME) /usr/local/bin/
	@mkdir -p /etc/backupd
	@cp config.yaml /etc/backupd/
	@echo "Installation completed"

docker-build:
	@echo "Building Docker image..."
	@docker build -t $(APP_NAME):$(VERSION) .

.PHONY: all build clean test tidy run once status help

BINARY_NAME=downsampler
BUILD_DIR=bin
CMD_DIR=cmd/downsampler

all: tidy build

tidy:
	go mod tidy

build:
	@echo "Building $(BINARY_NAME)..."
	@mkdir -p $(BUILD_DIR)
	go build -o $(BUILD_DIR)/$(BINARY_NAME) ./$(CMD_DIR)
	@echo "Build complete! Binary: $(BUILD_DIR)/$(BINARY_NAME)"

build-linux:
	@echo "Building Linux version..."
	@mkdir -p $(BUILD_DIR)
	GOOS=linux GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64 ./$(CMD_DIR)
	@echo "Linux build complete: $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64"

build-windows:
	@echo "Building Windows version..."
	@mkdir -p $(BUILD_DIR)
	GOOS=windows GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-windows-amd64.exe ./$(CMD_DIR)
	@echo "Windows build complete: $(BUILD_DIR)/$(BINARY_NAME)-windows-amd64.exe"

build-darwin:
	@echo "Building macOS version..."
	@mkdir -p $(BUILD_DIR)
	GOOS=darwin GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-amd64 ./$(CMD_DIR)
	GOOS=darwin GOARCH=arm64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-arm64 ./$(CMD_DIR)
	@echo "macOS builds complete"

build-all: build-linux build-windows build-darwin

run:
	go run ./$(CMD_DIR) --config configs/config.yaml

once:
	go run ./$(CMD_DIR) --config configs/config.yaml --once

status:
	go run ./$(CMD_DIR) --config configs/config.yaml --status

test:
	go test -v ./...

clean:
	@echo "Cleaning..."
	@rm -rf $(BUILD_DIR)
	@echo "Clean complete"

help:
	@echo "Available targets:"
	@echo "  all          - Run tidy and build (default)"
	@echo "  tidy         - Run go mod tidy"
	@echo "  build        - Build binary for current OS"
	@echo "  build-linux  - Build for Linux amd64"
	@echo "  build-windows - Build for Windows amd64"
	@echo "  build-darwin - Build for macOS (amd64 + arm64)"
	@echo "  build-all    - Build for all platforms"
	@echo "  run          - Run in daemon mode"
	@echo "  once         - Run once and exit"
	@echo "  status       - Show status"
	@echo "  test         - Run tests"
	@echo "  clean        - Remove build artifacts"
	@echo "  help         - Show this help"

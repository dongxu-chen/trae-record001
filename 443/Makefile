.PHONY: build test run clean docker-build docker-up docker-down lint format

BINARY_NAME := cross-cloud-lb
MAIN_PACKAGE := ./cmd/main.go

build:
	@echo "Building $(BINARY_NAME)..."
	@go build -o bin/$(BINARY_NAME) $(MAIN_PACKAGE)
	@echo "Build complete: bin/$(BINARY_NAME)"

test:
	@echo "Running tests..."
	@go test -v ./...

run: build
	@echo "Running $(BINARY_NAME)..."
	@./bin/$(BINARY_NAME) --config config.yaml

lint:
	@echo "Running linter..."
	@golangci-lint run ./...

format:
	@echo "Formatting code..."
	@go fmt ./...

docker-build:
	@echo "Building Docker image..."
	@docker build -t $(BINARY_NAME):latest -f deployments/docker/Dockerfile .

docker-up:
	@echo "Starting Docker Compose..."
	@docker-compose -f deployments/docker-compose.yml up -d

docker-down:
	@echo "Stopping Docker Compose..."
	@docker-compose -f deployments/docker-compose.yml down

k8s-deploy:
	@echo "Deploying to Kubernetes..."
	@kubectl apply -f deployments/k8s/control-plane.yaml
	@kubectl apply -f deployments/k8s/envoy-ds.yaml

k8s-undeploy:
	@echo "Undeploying from Kubernetes..."
	@kubectl delete -f deployments/k8s/control-plane.yaml
	@kubectl delete -f deployments/k8s/envoy-ds.yaml

clean:
	@echo "Cleaning up..."
	@rm -rf bin/
	@go clean

deps:
	@echo "Downloading dependencies..."
	@go mod download
	@go mod tidy

generate:
	@echo "Generating code..."
	@go generate ./...

all: deps build test

help:
	@echo "Available targets:"
	@echo "  build        - Build the binary"
	@echo "  test         - Run tests"
	@echo "  run          - Build and run"
	@echo "  lint         - Run linter"
	@echo "  format       - Format code"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-up    - Start Docker Compose"
	@echo "  docker-down  - Stop Docker Compose"
	@echo "  k8s-deploy   - Deploy to Kubernetes"
	@echo "  k8s-undeploy - Undeploy from Kubernetes"
	@echo "  clean        - Clean up"
	@echo "  deps         - Download dependencies"
	@echo "  all          - deps, build, test"

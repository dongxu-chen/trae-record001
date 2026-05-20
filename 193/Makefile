BINARY_NAME := k8s-auditor
DOCKER_IMAGE := k8s-auditor:latest

.PHONY: all build run test tidy docker-build docker-push deploy clean help

all: build

build:
	@echo "Building $(BINARY_NAME)..."
	@CGO_ENABLED=0 go build -o $(BINARY_NAME) ./cmd/auditor

run: build
	@echo "Running $(BINARY_NAME)..."
	@./$(BINARY_NAME) --once

tidy:
	@echo "Tidying Go modules..."
	@go mod tidy

docker-build:
	@echo "Building Docker image $(DOCKER_IMAGE)..."
	@docker build -t $(DOCKER_IMAGE) .

docker-push:
	@echo "Pushing Docker image $(DOCKER_IMAGE)..."
	@docker push $(DOCKER_IMAGE)

deploy:
	@echo "Deploying to Kubernetes..."
	@kubectl apply -f deploy/k8s/

clean:
	@echo "Cleaning up..."
	@rm -f $(BINARY_NAME)
	@rm -rf reports/

help:
	@echo "Available targets:"
	@echo "  all          - Build the binary (default)"
	@echo "  build        - Build the Go binary"
	@echo "  run          - Build and run once"
	@echo "  tidy         - Tidy Go modules"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-push  - Push Docker image to registry"
	@echo "  deploy       - Deploy to Kubernetes"
	@echo "  clean        - Clean build artifacts"
	@echo "  help         - Show this help message"

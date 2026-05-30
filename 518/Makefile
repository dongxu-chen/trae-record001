.PHONY: all build run test clean docker-build docker-push deploy

APP_NAME := kafka-autoscaler
VERSION := 1.0.0
IMAGE_NAME := $(APP_NAME):$(VERSION)

all: build

build:
	@echo "Building $(APP_NAME)..."
	go build -o bin/$(APP_NAME) ./cmd/main.go

run:
	@echo "Running $(APP_NAME)..."
	go run ./cmd/main.go -config config/config.yaml

test:
	@echo "Running tests..."
	go test -v ./...

clean:
	@echo "Cleaning..."
	rm -rf bin/
	go clean

docker-build:
	@echo "Building Docker image $(IMAGE_NAME)..."
	docker build -t $(IMAGE_NAME) .

docker-push:
	@echo "Pushing Docker image $(IMAGE_NAME)..."
	docker push $(IMAGE_NAME)

deploy:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f deploy/kubernetes/

undeploy:
	@echo "Undeploying from Kubernetes..."
	kubectl delete -f deploy/kubernetes/

fmt:
	@echo "Formatting code..."
	go fmt ./...

lint:
	@echo "Linting code..."
	golangci-lint run ./...

deps:
	@echo "Downloading dependencies..."
	go mod download
	go mod tidy

vendor:
	@echo "Vendoring dependencies..."
	go mod vendor

check: fmt lint test

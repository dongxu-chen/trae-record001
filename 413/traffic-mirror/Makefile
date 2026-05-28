.PHONY: all build wasm control-plane clean run test docker docker-build docker-up docker-down tls-gen

WASM_OUTPUT := wasm/output/traffic-mirror.wasm
CONTROL_PLANE_BIN := control-plane/bin/control-plane

all: build

build: wasm control-plane

wasm:
	@echo "Building Wasm plugin..."
	@mkdir -p wasm/output
	cd wasm && tinygo build -o ../wasm/output/traffic-mirror.wasm -target=wasi .

control-plane:
	@echo "Building control plane..."
	@mkdir -p control-plane/bin
	cd control-plane && CGO_ENABLED=1 go build -o bin/control-plane ./cmd/server/

tls-gen:
	@echo "Generating TLS certificates..."
	@mkdir -p envoy/tls
	cd envoy/tls && \
		openssl genrsa -out ca.key 2048 && \
		openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/CN=traffic-mirror-ca" && \
		openssl genrsa -out server.key 2048 && \
		openssl req -new -key server.key -out server.csr -subj "/CN=localhost" && \
		openssl x509 -req -days 3650 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt && \
		openssl genrsa -out client.key 2048 && \
		openssl req -new -key client.key -out client.csr -subj "/CN=client" && \
		openssl x509 -req -days 3650 -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt && \
		echo "TLS certificates generated in envoy/tls/"

clean:
	@echo "Cleaning..."
	rm -rf wasm/output
	rm -rf control-plane/bin
	rm -f control-plane/traffic-mirror.db

test:
	@echo "Running tests..."
	cd control-plane && go test ./...

run-control-plane: control-plane
	@echo "Running control plane..."
	cd control-plane && ./bin/control-plane --config control-plane.yaml

docker-build: tls-gen
	@echo "Building Docker images..."
	docker compose build

docker-up: tls-gen
	@echo "Starting all services..."
	docker compose up -d

docker-down:
	@echo "Stopping all services..."
	docker compose down

docker-logs:
	docker compose logs -f

docker-restart: docker-down docker-up

proto:
	@echo "Generating protobuf code..."
	cd proto && protoc --go_out=. --go-grpc_out=. *.proto

deps:
	@echo "Installing dependencies..."
	cd wasm && go mod tidy
	cd control-plane && go mod tidy

install-tinygo:
	@echo "Installing TinyGo..."
	@which tinygo || (echo "Please install TinyGo: https://tinygo.org/getting-started/install/" && exit 1)

help:
	@echo "Traffic Mirror Service Mesh Tool"
	@echo "================================"
	@echo ""
	@echo "Targets:"
	@echo "  make build              - Build Wasm plugin and control plane"
	@echo "  make wasm               - Build Wasm plugin only (requires TinyGo)"
	@echo "  make control-plane      - Build control plane only"
	@echo "  make tls-gen            - Generate TLS certificates for mTLS"
	@echo "  make clean              - Remove build artifacts"
	@echo "  make test               - Run tests"
	@echo "  make run-control-plane  - Run control plane locally"
	@echo "  make docker-build       - Build Docker images"
	@echo "  make docker-up          - Start all services"
	@echo "  make docker-down        - Stop all services"
	@echo "  make docker-logs        - View service logs"
	@echo "  make docker-restart     - Restart all services"
	@echo "  make deps               - Install Go dependencies"
	@echo "  make install-tinygo     - Check TinyGo installation"
	@echo ""
	@echo "Architecture:"
	@echo "  - Consistent Hash Sampling: Same request hash -> same mirror decision"
	@echo "  - TLS Termination: HTTPS traffic decrypted at Sidecar before mirroring"
	@echo "  - Proto Reflection: Dynamic protobuf message comparison via registered schemas"

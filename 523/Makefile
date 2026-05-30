APP_NAME := escape-detector
APP_VERSION := 1.0.0
BUILD_TIME := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

GO ?= go
GOFLAGS ?=
LDFLAGS := -ldflags "-X main.version=$(APP_VERSION) -X main.buildTime=$(BUILD_TIME) -X main.gitCommit=$(GIT_COMMIT)"

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
CONFDIR ?= /etc/escape-detector

CLANG ?= clang
LLVM_STRIP ?= llvm-strip

BPF_SRC := internal/ebpf/probes/escape_detect.bpf.c
BPF_OBJ := internal/ebpf/probes/escape_detect_bpfel.o
BPF_GO := internal/ebpf/escape_detect_bpfel.go

all: build

.PHONY: build
build: generate-bpf
	@echo "Building $(APP_NAME) $(APP_VERSION)..."
	$(GO) build $(GOFLAGS) $(LDFLAGS) -o cmd/$(APP_NAME)/$(APP_NAME) ./cmd/$(APP_NAME)
	@echo "Build complete: cmd/$(APP_NAME)/$(APP_NAME)"

.PHONY: generate-bpf
generate-bpf: $(BPF_GO)

$(BPF_GO): $(BPF_SRC)
	@echo "Generating eBPF bindings..."
	@if command -v bpf2go >/dev/null 2>&1; then \
		cd internal/ebpf/probes && \
		bpf2go -cc $(CLANG) -strip $(LLVM_STRIP) -target amd64 escape_detect ../../$(BPF_SRC); \
		mv escape_detect_bpfel.go ../; \
		echo "eBPF bindings generated"; \
	else \
		echo "WARNING: bpf2go not found, using fallback generated code"; \
		echo "Install with: go install github.com/cilium/ebpf/cmd/bpf2go@latest"; \
	fi

.PHONY: test
test:
	@echo "Running tests..."
	$(GO) test -v ./pkg/... ./internal/...
	@echo "Tests complete"

.PHONY: test-short
test-short:
	@echo "Running short tests..."
	$(GO) test -short -v ./pkg/... ./internal/...

.PHONY: lint
lint:
	@echo "Running linter..."
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run ./...; \
	else \
		echo "WARNING: golangci-lint not found"; \
		$(GO) vet ./...; \
	fi

.PHONY: fmt
fmt:
	@echo "Formatting code..."
	$(GO) fmt ./...
	@echo "Format complete"

.PHONY: vet
vet:
	@echo "Running go vet..."
	$(GO) vet ./...
	@echo "Vet complete"

.PHONY: install
install: build
	@echo "Installing $(APP_NAME)..."
	install -d $(DESTDIR)$(BINDIR)
	install -m 755 cmd/$(APP_NAME)/$(APP_NAME) $(DESTDIR)$(BINDIR)/$(APP_NAME)
	install -d $(DESTDIR)$(CONFDIR)
	install -d $(DESTDIR)$(CONFDIR)/rules
	install -m 644 configs/config.yaml $(DESTDIR)$(CONFDIR)/config.yaml
	install -m 640 configs/rules/*.yaml $(DESTDIR)$(CONFDIR)/rules/
	@echo "Install complete"

.PHONY: uninstall
uninstall:
	@echo "Uninstalling $(APP_NAME)..."
	rm -f $(DESTDIR)$(BINDIR)/$(APP_NAME)
	rm -rf $(DESTDIR)$(CONFDIR)
	@echo "Uninstall complete"

.PHONY: run
run: build
	@echo "Running $(APP_NAME) in test mode..."
	sudo cmd/$(APP_NAME)/$(APP_NAME) --test --log-level debug

.PHONY: run-real
run-real: build
	@echo "Running $(APP_NAME)..."
	sudo cmd/$(APP_NAME)/$(APP_NAME) --config configs/config.yaml

.PHONY: clean
clean:
	@echo "Cleaning..."
	rm -f cmd/$(APP_NAME)/$(APP_NAME)
	rm -f $(BPF_OBJ)
	$(GO) clean ./...
	@echo "Clean complete"

.PHONY: deps
deps:
	@echo "Installing dependencies..."
	$(GO) mod download
	$(GO) mod verify
	@echo "Dependencies installed"

.PHONY: deps-update
deps-update:
	@echo "Updating dependencies..."
	$(GO) get -u ./...
	$(GO) mod tidy
	@echo "Dependencies updated"

.PHONY: check-rules
check-rules: build
	@echo "Checking loaded rules..."
	cmd/$(APP_NAME)/$(APP_NAME) --dump-rules

.PHONY: list-containers
list-containers: build
	@echo "Listing containers..."
	sudo cmd/$(APP_NAME)/$(APP_NAME) --list-containers

.PHONY: version
version:
	@echo "$(APP_NAME) $(APP_VERSION)"
	@echo "Build time: $(BUILD_TIME)"
	@echo "Git commit: $(GIT_COMMIT)"

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build              - Build the application"
	@echo "  generate-bpf       - Generate eBPF Go bindings (requires bpf2go)"
	@echo "  test               - Run all tests"
	@echo "  test-short         - Run short tests"
	@echo "  lint               - Run linter"
	@echo "  fmt                - Format code"
	@echo "  vet                - Run go vet"
	@echo "  install            - Install to system"
	@echo "  uninstall          - Uninstall from system"
	@echo "  run                - Run in test mode"
	@echo "  run-real           - Run in real mode"
	@echo "  clean              - Clean build artifacts"
	@echo "  deps               - Download dependencies"
	@echo "  deps-update        - Update dependencies"
	@echo "  check-rules        - List all loaded detection rules"
	@echo "  list-containers    - List detected containers"
	@echo "  version            - Show version information"
	@echo "  help               - Show this help"

.DEFAULT_GOAL := build

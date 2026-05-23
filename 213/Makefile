.PHONY: build clean install test

BINARY_NAME=monitor-agent
BUILD_DIR=build
INSTALL_DIR=/opt/monitor-agent
SYSTEMD_DIR=/etc/systemd/system

build:
	@echo "Building $(BINARY_NAME)..."
	@mkdir -p $(BUILD_DIR)
	go build -o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/monitor-agent
	@echo "Build complete!"

clean:
	@echo "Cleaning..."
	@rm -rf $(BUILD_DIR)
	@echo "Clean complete!"

test:
	@echo "Running tests..."
	go test -v ./...
	@echo "Tests complete!"

install: build
	@echo "Installing $(BINARY_NAME)..."
	@mkdir -p $(INSTALL_DIR)
	@cp $(BUILD_DIR)/$(BINARY_NAME) $(INSTALL_DIR)/
	@cp config.yaml $(INSTALL_DIR)/
	@cp deploy/monitor-agent.service $(SYSTEMD_DIR)/
	@systemctl daemon-reload
	@echo "Install complete!"
	@echo "Run 'systemctl start $(BINARY_NAME)' to start the service"
	@echo "Run 'systemctl enable $(BINARY_NAME)' to enable on boot"

uninstall:
	@echo "Uninstalling $(BINARY_NAME)..."
	@systemctl stop $(BINARY_NAME) 2>/dev/null || true
	@systemctl disable $(BINARY_NAME) 2>/dev/null || true
	@rm -rf $(INSTALL_DIR)
	@rm -f $(SYSTEMD_DIR)/monitor-agent.service
	@systemctl daemon-reload
	@echo "Uninstall complete!"

run: build
	@echo "Running $(BINARY_NAME)..."
	$(BUILD_DIR)/$(BINARY_NAME) --config config.yaml

.PHONY: all build test clean run docker-build docker-up docker-down

BINARY_NAME=kafka-lag-analyzer
MAIN_PACKAGE=./cmd/analyzer

all: build

build:
	go build -o $(BINARY_NAME) $(MAIN_PACKAGE)

test:
	go test -v ./...

clean:
	rm -f $(BINARY_NAME)
	go clean

run: build
	./$(BINARY_NAME) --config config.yaml

deps:
	go mod download
	go mod tidy

docker-build:
	docker build -t kafka-lag-analyzer:latest -f deployments/docker/Dockerfile .

docker-up:
	cd deployments/docker && docker-compose up -d

docker-down:
	cd deployments/docker && docker-compose down

docker-logs:
	cd deployments/docker && docker-compose logs -f

kafka-topic:
	docker exec -it kafka kafka-topics --create --topic test-topic --bootstrap-server localhost:9092 --partitions 6 --replication-factor 1

kafka-produce:
	docker exec -it kafka bash -c "seq 10000 | kafka-console-producer --broker-list localhost:9092 --topic test-topic"

kafka-consume:
	docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic test-topic --from-beginning --group test-group

check-endpoints:
	@echo "Health check:"
	@curl -s http://localhost:8080/health
	@echo ""
	@echo "Groups:"
	@curl -s http://localhost:8080/api/groups | python3 -m json.tool
	@echo ""
	@echo "Metrics (first 50 lines):"
	@curl -s http://localhost:8080/metrics | head -50

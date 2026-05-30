.PHONY: help build backend frontend run test clean docker-up docker-down

help:
	@echo "Available targets:"
	@echo "  make backend    - Build Go backend"
	@echo "  make frontend   - Install frontend dependencies"
	@echo "  make run        - Run backend locally"
	@echo "  make demo       - Inject demo flow data"
	@echo "  make docker-up  - Start all services with Docker Compose"
	@echo "  make docker-down - Stop all services"
	@echo "  make clean      - Clean build artifacts"

backend:
	cd backend && go build -o ../bin/server .

frontend:
	cd frontend && npm install

run:
	cd backend && go run main.go

demo:
	@powershell -ExecutionPolicy Bypass -File scripts/demo-flows.ps1

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

neo4j:
	docker-compose up -d neo4j

clean:
	rm -rf bin/
	rm -rf frontend/node_modules/
	rm -rf frontend/dist/

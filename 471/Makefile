.PHONY: all build backend frontend csi sidecar clean test deps run run-sidecar docker-build docker-up docker-down

all: build

deps:
	go mod download
	cd frontend && npm install

build: backend frontend csi sidecar

backend:
	go build -o bin/keymgmt-server ./backend/cmd/server

frontend:
	cd frontend && npm run build

csi:
	go build -o bin/csi-driver ./csi-driver/cmd

sidecar:
	go build -o bin/keymgmt-sidecar ./sidecar/cmd

test:
	go test ./...

run:
	go run ./backend/cmd/server

run-frontend:
	cd frontend && npm run dev

run-sidecar:
	go run ./sidecar/cmd \
		--target=http://localhost:8081 \
		--listen=:8080 \
		--api-url=http://localhost:8080 \
		--watch-paths=/secrets \
		--poll-interval=30 \
		--inject-headers=true

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

k8s-deploy:
	kubectl apply -f k8s/keymgmt-service.yaml
	kubectl apply -f k8s/csi-driver-simple.yaml

k8s-deploy-with-rbac:
	kubectl apply -f k8s/keymgmt-service.yaml
	kubectl apply -f k8s/csi-driver.yaml

k8s-delete:
	-kubectl delete -f k8s/csi-driver.yaml
	-kubectl delete -f k8s/csi-driver-simple.yaml
	-kubectl delete -f k8s/keymgmt-service.yaml

clean:
	rm -rf bin/
	rm -rf frontend/dist/
	rm -rf data/

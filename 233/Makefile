.PHONY: all build test clean run docker-build

all: build

build:
	go build -o bin/autoscaler ./cmd/autoscaler

test:
	go test -v ./...

clean:
	rm -rf bin/

run: build
	./bin/autoscaler -config examples/config-aws.yaml -dry-run

docker-build:
	docker build -t cloud-autoscaler:latest .

terraform-init:
	cd terraform && terraform init

terraform-plan:
	cd terraform && terraform plan

terraform-apply:
	cd terraform && terraform apply

deps:
	go mod tidy
	go mod download

.PHONY: all build ebpf clean run test

all: build

ebpf:
	clang -O2 -g -target bpf -c bpf/process_monitor.bpf.c -o bpf/process_monitor_bpfel.o
	clang -O2 -g -target bpf -c bpf/file_monitor.bpf.c -o bpf/file_monitor_bpfel.o
	clang -O2 -g -target bpf -c bpf/network_monitor.bpf.c -o bpf/network_monitor_bpfel.o

build: ebpf
	go build -o bin/csm main.go

clean:
	rm -rf bin/
	rm -f bpf/*.o

run: build
	sudo ./bin/csm

test:
	go test -v ./...

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

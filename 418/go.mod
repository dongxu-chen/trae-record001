module github.com/coldstart-optimizer/coldstart

go 1.22

require (
	github.com/cilium/ebpf v0.14.0
	github.com/opencontainers/runtime-spec v1.1.0
	github.com/opencontainers/image-spec v1.1.0
	github.com/docker/docker v27.1.1+incompatible
	github.com/docker/go-connections v0.5.0
	github.com/containerd/containerd v1.7.22
	go.opentelemetry.io/otel v1.28.0
	go.opentelemetry.io/otel/exporters/jaeger v1.17.0
	go.opentelemetry.io/otel/sdk v1.28.0
	go.opentelemetry.io/otel/trace v1.28.0
	github.com/prometheus/client_golang v1.19.1
	github.com/prometheus/client_model v0.6.1
	github.com/prometheus/common v0.54.0
	github.com/urfave/cli/v2 v2.27.1
	github.com/mackerelio/go-osstat v0.2.6
	github.com/shirou/gopsutil/v3 v3.24.5
	golang.org/x/sys v0.24.0
)

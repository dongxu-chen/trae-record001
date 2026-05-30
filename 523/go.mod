module github.com/security/container-escape-detector

go 1.21

require (
	github.com/cilium/ebpf v0.12.3
	github.com/prometheus/client_golang v1.17.0
	github.com/prometheus/client_model v0.5.0
	github.com/prometheus/common v0.45.0
	gopkg.in/yaml.v3 v3.0.1
	github.com/sirupsen/logrus v1.9.3
	github.com/spf13/viper v1.18.2
	github.com/docker/docker v24.0.7+incompatible
	github.com/opencontainers/runtime-spec v1.1.0
	github.com/shirou/gopsutil/v3 v3.23.11
	github.com/google/uuid v1.4.0
)

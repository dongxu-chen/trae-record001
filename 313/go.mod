module ci-scheduler

go 1.21

require (
	github.com/robfig/cron/v3 v3.0.1
	github.com/spf13/cobra v1.7.0
	golang.org/x/sync v0.5.0
	k8s.io/api v0.28.3
	k8s.io/apimachinery v0.28.3
	k8s.io/client-go v0.28.3
	gopkg.in/yaml.v3 v3.0.1
	github.com/shirou/gopsutil/v3 v3.23.10
)

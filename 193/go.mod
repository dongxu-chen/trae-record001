module k8s-auditor

go 1.21

require (
	k8s.io/api v0.29.0
	k8s.io/apimachinery v0.29.0
	k8s.io/client-go v0.29.0
	github.com/robfig/cron/v3 v3.0.1
	github.com/spf13/viper v1.18.2
	gopkg.in/yaml.v3 v3.0.1
	github.com/sirupsen/logrus v1.9.3
)

require (
	github.com/fsnotify/fsnotify v1.7.0
	github.com/hashicorp/hcl v1.0.0
	github.com/magiconair/properties v1.8.7
	github.com/mitchellh/mapstructure v1.5.0
	github.com/pelletier/go-toml/v2 v2.1.0
	github.com/spf13/afero v1.11.0
	github.com/spf13/cast v1.6.0
	github.com/spf13/jwalterweatherman v1.1.0
	github.com/spf13/pflag v1.0.5
	github.com/subosito/gotenv v1.6.0
	golang.org/x/sys v0.15.0
	golang.org/x/text v0.14.0
	k8s.io/klog/v2 v2.110.1
	k8s.io/utils v0.0.0-20230726121419-3b25d923346b
	sigs.k8s.io/structured-merge-diff/v4 v4.4.1
	sigs.k8s.io/yaml v1.4.0
)

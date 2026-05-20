module backup-tool

go 1.21

require (
	github.com/aws/aws-sdk-go-v2 v1.21.0
	github.com/aws/aws-sdk-go-v2/config v1.18.32
	github.com/aws/aws-sdk-go-v2/feature/s3/manager v1.11.76
	github.com/aws/aws-sdk-go-v2/service/s3 v1.38.1
	github.com/go-sql-driver/mysql v1.7.1
	github.com/google/uuid v1.4.0
	github.com/prometheus/client_golang v1.17.0
	github.com/sirupsen/logrus v1.9.3
	github.com/spf13/viper v1.17.0
	golang.org/x/crypto v0.14.0
	gopkg.in/natefinch/lumberjack.v2 v2.2.1
	gopkg.in/yaml.v3 v3.0.1
)

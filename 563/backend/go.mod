module etcd-backup-manager

go 1.21

require (
	go.etcd.io/etcd/client/v3 v3.5.10
	github.com/gin-gonic/gin v1.9.1
	github.com/robfig/cron/v3 v3.0.1
	github.com/aws/aws-sdk-go-v2 v1.21.0
	github.com/aws/aws-sdk-go-v2/config v1.18.39
	github.com/aws/aws-sdk-go-v2/service/s3 v1.38.2
	github.com/minio/minio-go/v7 v7.0.63
	golang.org/x/crypto v0.14.0
	github.com/google/uuid v1.3.0
	gopkg.in/yaml.v3 v3.0.1
	github.com/shirou/gopsutil/v3 v3.23.9
)

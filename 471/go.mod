module github.com/keymgmt/service

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/hashicorp/vault/api v1.10.0
	github.com/aws/aws-sdk-go-v2 v1.21.0
	github.com/aws/aws-sdk-go-v2/service/kms v1.24.0
	github.com/aws/aws-sdk-go-v2/config v1.18.45
	k8s.io/api v0.28.0
	k8s.io/apimachinery v0.28.0
	k8s.io/client-go v0.28.0
	github.com/container-storage-interface/spec v1.8.0
	golang.org/x/net v0.17.0
	google.golang.org/grpc v1.59.0
	github.com/google/uuid v1.3.0
	gorm.io/gorm v1.25.5
	gorm.io/driver/sqlite v1.5.4
	github.com/sirupsen/logrus v1.9.3
	github.com/spf13/viper v1.17.0
	golang.org/x/crypto v0.14.0
	github.com/fsnotify/fsnotify v1.7.0
)

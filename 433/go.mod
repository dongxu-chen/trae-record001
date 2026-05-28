module k8s-cost-allocation

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/prometheus/client_golang v1.17.0
	github.com/prometheus/common v0.44.0
	k8s.io/api v0.28.4
	k8s.io/apimachinery v0.28.4
	k8s.io/client-go v0.28.4
	github.com/aws/aws-sdk-go-v2 v1.21.2
	github.com/aws/aws-sdk-go-v2/config v1.18.45
	github.com/aws/aws-sdk-go-v2/service/costexplorer v1.28.3
	gopkg.in/yaml.v3 v3.0.1
	github.com/shopspring/decimal v1.3.1
)

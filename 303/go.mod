module autoscaler

go 1.21

require (
	github.com/prometheus/client_golang v1.19.0
	github.com/prometheus/common v0.52.3
	gopkg.in/yaml.v3 v3.0.1
	github.com/spf13/cobra v1.8.0
	github.com/aliyun/alibaba-cloud-sdk-go v1.62.687
	github.com/aws/aws-sdk-go-v2 v1.27.0
	github.com/aws/aws-sdk-go-v2/config v1.27.0
	github.com/aws/aws-sdk-go-v2/service/autoscaling v1.32.0
	github.com/aws/aws-sdk-go-v2/service/ec2 v1.157.0
	go.uber.org/zap v1.27.0
)

module cross-cloud-lb

go 1.21

require (
	github.com/envoyproxy/go-control-plane v0.12.0
	github.com/aws/aws-sdk-go-v2 v1.24.0
	github.com/aws/aws-sdk-go-v2/config v1.26.0
	github.com/aws/aws-sdk-go-v2/service/eks v1.34.0
	github.com/Azure/azure-sdk-for-go/sdk/azcore v1.9.0
	github.com/Azure/azure-sdk-for-go/sdk/azidentity v1.4.0
	github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/containerservice/armcontainerservice/v4 v4.6.0
	github.com/google/uuid v1.5.0
	google.golang.org/api v0.154.0
	google.golang.org/genproto/googleapis/cloud/container v1.22.0
	google.golang.org/grpc v1.60.0
	google.golang.org/protobuf v1.32.0
	github.com/prometheus/client_golang v1.18.0
	github.com/spf13/viper v1.18.2
	go.uber.org/zap v1.26.0
	golang.org/x/net v0.20.0
	k8s.io/api v0.29.0
	k8s.io/apimachinery v0.29.0
	k8s.io/client-go v0.29.0
)

module servicemesh-gateway

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/go-redis/redis/v8 v8.11.5
	github.com/google/uuid v1.4.0
	github.com/spf13/viper v1.17.0
	github.com/zeromicro/go-zero v1.5.5
	istio.io/api v1.20.0
	istio.io/client-go v1.20.0
	k8s.io/apimachinery v0.28.4
	k8s.io/client-go v0.28.4
	sigs.k8s.io/yaml v1.3.0
)

require (
	github.com/davecgh/go-spew v1.1.1
	github.com/gin-contrib/cors v1.5.0
	github.com/prometheus/client_golang v1.17.0
)

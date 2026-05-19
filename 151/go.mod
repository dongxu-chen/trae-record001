module servicemesh-console

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/sirupsen/logrus v1.9.3
	k8s.io/api v0.28.4
	k8s.io/apimachinery v0.28.4
	k8s.io/client-go v0.28.4
	istio.io/api v1.18.2
	istio.io/client-go v1.18.2
	go.opentelemetry.io/otel v1.19.0
	go.opentelemetry.io/otel/trace v1.19.0
	go.opentelemetry.io/otel/sdk v1.19.0
	go.opentelemetry.io/otel/propagation v1.19.0
	go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin v0.44.0
	google.golang.org/grpc v1.59.0
)

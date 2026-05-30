module k8s-network-policy-recommender

go 1.21

require (
	github.com/neo4j/neo4j-go-driver/v5 v5.17.0
	github.com/gin-gonic/gin v1.9.1
	github.com/spf13/viper v1.18.2
	k8s.io/api v0.29.0
	k8s.io/apimachinery v0.29.0
	k8s.io/client-go v0.29.0
	github.com/prometheus/client_golang v1.18.0
	github.com/sirupsen/logrus v1.9.3
	gopkg.in/yaml.v3 v3.0.1
)

package main

import (
	"log"
	"os"
	"strings"

	"github.com/spf13/viper"

	"servicemesh-gateway/pkg/accesscontrol"
	"servicemesh-gateway/pkg/api"
	"servicemesh-gateway/pkg/bluegreen"
	"servicemesh-gateway/pkg/costestimator"
	"servicemesh-gateway/pkg/istio"
	redisclient "servicemesh-gateway/pkg/redis"
)

func main() {
	initConfig()

	redisConfig := redisclient.Config{
		Addr:     viper.GetString("redis.addr"),
		Password: viper.GetString("redis.password"),
		DB:       viper.GetInt("redis.db"),
	}

	redisClient, err := redisclient.NewClient(redisConfig)
	if err != nil {
		log.Printf("Warning: Failed to connect to Redis: %v", err)
		log.Println("Continuing without Redis cache...")
	} else {
		defer redisClient.Close()
		log.Println("Connected to Redis successfully")
	}

	trafficStore := redisclient.NewTrafficStore(redisClient)

	kubeconfig := viper.GetString("kubeconfig")
	istioClient, err := istio.NewClient(kubeconfig)
	if err != nil {
		log.Printf("Warning: Failed to create Istio client: %v", err)
		log.Println("Continuing in simulation mode...")
	} else {
		log.Println("Istio client created successfully")
	}

	bgm := bluegreen.NewBlueGreenManager(istioClient, trafficStore)
	defer bgm.Stop()
	log.Println("Blue-green deployment manager started")

	acm := accesscontrol.NewAccessControlManager(istioClient, trafficStore)
	log.Println("Access control manager initialized")

	ce := costestimator.NewCostEstimator()
	log.Println("Cost estimator initialized")

	router := api.SetupRouter(istioClient, trafficStore, bgm, acm, ce)

	port := viper.GetString("server.port")
	if port == "" {
		port = "8080"
	}

	log.Printf("Server starting on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func initConfig() {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./config")
	viper.AddConfigPath("/etc/servicemesh-gateway")
	viper.AddConfigPath(".")

	viper.SetEnvPrefix("SMG")
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err != nil {
		log.Printf("Warning: No config file found, using environment variables and defaults")
	}

	setDefaults()
}

func setDefaults() {
	viper.SetDefault("server.port", "8080")
	viper.SetDefault("redis.addr", "localhost:6379")
	viper.SetDefault("redis.password", "")
	viper.SetDefault("redis.db", 0)

	if kubeconfig := os.Getenv("KUBECONFIG"); kubeconfig != "" {
		viper.SetDefault("kubeconfig", kubeconfig)
	}
}

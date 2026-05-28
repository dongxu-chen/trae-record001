package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/spf13/viper"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	"github.com/traffic-mirror/control-plane/internal/api"
	"github.com/traffic-mirror/control-plane/internal/compare"
	"github.com/traffic-mirror/control-plane/internal/config"
	"github.com/traffic-mirror/control-plane/internal/model"
	"github.com/traffic-mirror/control-plane/internal/tracing"
	"github.com/traffic-mirror/control-plane/internal/xds"
)

func main() {
	var configFile string
	flag.StringVar(&configFile, "config", "", "path to config file")
	flag.Parse()

	if err := loadConfig(configFile); err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	apiAddr := viper.GetString("api.addr")
	xdsAddr := viper.GetString("xds.addr")
	dbPath := viper.GetString("db.path")
	prodHost := viper.GetString("envoy.production.host")
	prodPort := viper.GetUint32("envoy.production.port")
	testHost := viper.GetString("envoy.test.host")
	testPort := viper.GetUint32("envoy.test.port")
	wasmPlugin := viper.GetString("envoy.wasm_plugin")
	jaegerEndpoint := viper.GetString("jaeger.endpoint")

	db, err := gorm.Open(sqlite.Open(dbPath), &gorm.Config{})
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}

	if err := model.AutoMigrate(db); err != nil {
		log.Fatalf("failed to migrate database: %v", err)
	}

	var jaegerTracer *tracing.JaegerTracer
	if jaegerEndpoint != "" {
		jaegerTracer, err = tracing.NewJaegerTracer("traffic-mirror-control-plane", jaegerEndpoint)
		if err != nil {
			log.Printf("warning: failed to initialize Jaeger: %v", err)
		} else {
			defer jaegerTracer.Shutdown(context.Background())
		}
	}

	configMgr := config.NewManager(db)
	compareStore := compare.NewStore(db)

	nodeID := viper.GetString("envoy.node_id")
	if nodeID == "" {
		nodeID = "traffic-mirror-envoy"
	}

	xdsServer := xds.NewXDSServer(nodeID, prodHost, prodPort, testHost, testPort, wasmPlugin)

	initialConfigJSON := configMgr.GetConfigJSON()
	if err := xdsServer.UpdateConfig(initialConfigJSON); err != nil {
		log.Printf("warning: initial xDS config update failed: %v", err)
	}

	xdsUpdater := func(configJSON string) error {
		return xdsServer.UpdateConfig(configJSON)
	}

	gin.SetMode(gin.ReleaseMode)
	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(jaegerMiddleware(jaegerTracer))

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	router.GET("/metrics", gin.WrapH(promhttp.Handler()))

	handler := api.NewHandler(configMgr, compareStore, jaegerTracer, xdsUpdater)
	handler.RegisterRoutes(router)

	apiServer := &http.Server{
		Addr:         apiAddr,
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
	}

	grpcListener, err := net.Listen("tcp", xdsAddr)
	if err != nil {
		log.Fatalf("failed to listen on xDS address %s: %v", xdsAddr, err)
	}

	grpcServer := grpc.NewServer()
	xdsServer.RegisterGRPC(grpcServer)

	go func() {
		log.Printf("gRPC xDS server listening on %s", xdsAddr)
		if err := grpcServer.Serve(grpcListener); err != nil {
			log.Fatalf("gRPC server error: %v", err)
		}
	}()

	go func() {
		log.Printf("HTTP API server listening on %s", apiAddr)
		if err := apiServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("HTTP server error: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("shutting down servers...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	grpcServer.GracefulStop()
	if err := apiServer.Shutdown(ctx); err != nil {
		log.Printf("HTTP server shutdown error: %v", err)
	}

	log.Println("servers stopped")
}

func loadConfig(path string) error {
	viper.SetConfigName("control-plane")
	viper.SetConfigType("yaml")

	if path != "" {
		viper.SetConfigFile(path)
	}

	viper.AddConfigPath(".")
	viper.AddConfigPath("/etc/traffic-mirror/")
	viper.AddConfigPath("$HOME/.traffic-mirror/")

	viper.SetDefault("api.addr", ":8080")
	viper.SetDefault("xds.addr", ":18000")
	viper.SetDefault("db.path", "traffic-mirror.db")
	viper.SetDefault("envoy.node_id", "traffic-mirror-envoy")
	viper.SetDefault("envoy.production.host", "localhost")
	viper.SetDefault("envoy.production.port", 9090)
	viper.SetDefault("envoy.test.host", "localhost")
	viper.SetDefault("envoy.test.port", 9091)
	viper.SetDefault("envoy.wasm_plugin", "/etc/envoy/wasm/traffic-mirror.wasm")
	viper.SetDefault("jaeger.endpoint", "")

	return viper.ReadInConfig()
}

func jaegerMiddleware(tracer *tracing.JaegerTracer) gin.HandlerFunc {
	return func(c *gin.Context) {
		if tracer == nil {
			c.Next()
			return
		}

		ctx, span := tracer.Tracer().Start(
			c.Request.Context(),
			fmt.Sprintf("%s %s", c.Request.Method, c.FullPath()),
			trace.WithAttributes(
				attribute.String("http.method", c.Request.Method),
				attribute.String("http.path", c.Request.URL.Path),
			),
		)
		defer span.End()

		c.Request = c.Request.WithContext(ctx)
		c.Next()

		span.SetAttributes(
			attribute.Int("http.status_code", c.Writer.Status()),
		)
	}
}

func init() {
	otel.SetTextMapPropagator(otel.GetTextMapPropagator())
}

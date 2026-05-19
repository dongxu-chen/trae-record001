package server

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"servicemesh-console/pkg/handler"
	"servicemesh-console/pkg/tracing"
)

type Server struct {
	port     string
	handlers *handler.Handlers
}

func NewServer(port string, handlers *handler.Handlers) *Server {
	return &Server{
		port:     port,
		handlers: handlers,
	}
}

func (s *Server) Start() error {
	if os.Getenv("GIN_MODE") == "" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(gin.Logger())

	r.Use(otelgin.Middleware("servicemesh-console"))
	r.Use(tracing.GetTraceHeadersMiddleware())
	r.Use(tracing.ResponseLoggerMiddleware())
	r.Use(handler.SamplingMiddleware())
	r.Use(handler.SmartRouteMiddleware())
	r.Use(handler.AnomalyDetectionMiddleware())
	r.Use(handler.TrafficRecordingMiddleware())

	api := r.Group("/api/v1")
	{
		api.GET("/health", s.handlers.HealthCheck)

		mirror := api.Group("/traffic-mirror")
		{
			mirror.POST("", s.handlers.ConfigureTrafficMirror)
			mirror.GET("", s.handlers.GetTrafficMirrorConfig)
			mirror.DELETE("/:service", s.handlers.DeleteTrafficMirrorConfig)
		}

		canary := api.Group("/canary-release")
		{
			canary.POST("", s.handlers.ConfigureCanaryRelease)
			canary.GET("", s.handlers.GetCanaryReleaseConfig)
			canary.DELETE("/:service", s.handlers.DeleteCanaryReleaseConfig)
			canary.PATCH("/:service/traffic", s.handlers.UpdateCanaryTraffic)
			canary.POST("/:service/gradual-start", s.handlers.StartGradualTrafficUpdate)
			canary.POST("/:service/gradual-stop", s.handlers.StopGradualTrafficUpdate)
		}

		fault := api.Group("/fault-injection")
		{
			fault.POST("", s.handlers.ConfigureFaultInjection)
			fault.GET("", s.handlers.GetFaultInjectionConfig)
			fault.DELETE("/:service", s.handlers.DeleteFaultInjectionConfig)
		}

		cb := api.Group("/circuit-breaker")
		{
			cb.POST("", s.handlers.ConfigureCircuitBreaker)
			cb.GET("", s.handlers.GetCircuitBreakerConfig)
			cb.DELETE("/:service", s.handlers.DeleteCircuitBreakerConfig)
			cb.GET("/:service/verify", s.handlers.VerifyCircuitBreaker)
		}

		sampling := api.Group("/sampling")
		{
			sampling.POST("", s.handlers.ConfigureSampling)
			sampling.GET("", s.handlers.GetSamplingConfig)
			sampling.DELETE("/:service", s.handlers.DeleteSamplingConfig)
		}

		smartRoute := api.Group("/smart-route")
		{
			smartRoute.POST("", s.handlers.ConfigureSmartRoute)
			smartRoute.GET("", s.handlers.GetSmartRouteConfig)
			smartRoute.DELETE("/:service", s.handlers.DeleteSmartRouteConfig)
		}

		anomaly := api.Group("/anomaly-detection")
		{
			anomaly.POST("", s.handlers.ConfigureAnomalyDetection)
			anomaly.GET("", s.handlers.GetAnomalyDetectionConfig)
			anomaly.DELETE("/:service", s.handlers.DeleteAnomalyDetectionConfig)
			anomaly.GET("/instances", s.handlers.GetInstanceStatus)
			anomaly.POST("/eject", s.handlers.EjectInstance)
			anomaly.POST("/restore", s.handlers.RestoreInstance)
		}

		topology := api.Group("/topology")
		{
			topology.GET("", s.handlers.GetTrafficTopology)
			topology.GET("/metrics/:service", s.handlers.GetServiceMetrics)
			topology.DELETE("/data", s.handlers.ClearTrafficData)
		}
	}

	srv := &http.Server{
		Addr:    ":" + s.port,
		Handler: r,
	}

	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	log.Printf("Server started on port %s", s.port)

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
		return err
	}

	log.Println("Server exited properly")
	return nil
}

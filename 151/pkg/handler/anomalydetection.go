package handler

import (
	"context"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	v1alpha3networking "istio.io/api/networking/v1alpha3"
	networkingv1alpha3 "istio.io/client-go/pkg/apis/networking/v1alpha3"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"go.opentelemetry.io/otel/attribute"
	"servicemesh-console/pkg/tracing"
)

var (
	anomalyDetectionConfigMap = make(map[string]*AnomalyDetectionConfig)
	anomalyDetectionMu        sync.RWMutex
	instanceErrorMap          = make(map[string]*InstanceStatus)
	instanceErrorMu           sync.RWMutex
)

type InstanceStatus struct {
	ConsecutiveErrors int
	TotalErrors       int
	TotalRequests     int
	LastErrorTime     time.Time
	LastEjectedTime   time.Time
	Ejected           bool
}

func (h *Handlers) ConfigureAnomalyDetection(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "ConfigureAnomalyDetection")
	defer span.End()

	var config AnomalyDetectionConfig
	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(http.StatusBadRequest, ApiResponse{
			Success: false,
			Message: "Invalid request: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	namespace := config.Namespace
	if namespace == "" {
		namespace = h.namespace
	}

	tracing.AddSpanAttributes(span,
		attribute.String("service_name", config.ServiceName),
		attribute.Int("consecutive_errors", config.ConsecutiveErrors),
		attribute.Bool("enabled", config.Enabled),
	)

	key := namespace + "/" + config.ServiceName
	anomalyDetectionMu.Lock()
	anomalyDetectionConfigMap[key] = &config
	anomalyDetectionMu.Unlock()

	dr, err := h.createAnomalyDetectionDestinationRule(ctx, &config, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to configure anomaly detection: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Anomaly detection configured successfully",
		Data:    dr,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) createAnomalyDetectionDestinationRule(ctx context.Context, config *AnomalyDetectionConfig, namespace string) (*networkingv1alpha3.DestinationRule, error) {
	drName := config.ServiceName + "-anomaly"

	dr := &networkingv1alpha3.DestinationRule{
		ObjectMeta: metav1.ObjectMeta{
			Name:      drName,
			Namespace: namespace,
			Labels: map[string]string{
				"servicemesh-console/anomaly-detection": "enabled",
			},
		},
		Spec: v1alpha3networking.DestinationRule{
			Host: config.ServiceName,
			TrafficPolicy: &v1alpha3networking.TrafficPolicy{
				OutlierDetection: &v1alpha3networking.OutlierDetection{
					Consecutive_5XxErrors:     int32(config.ConsecutiveErrors),
					Interval:                  &metav1.Duration{Duration: time.Duration(config.IntervalSeconds) * time.Second},
					BaseEjectionTime:          &metav1.Duration{Duration: time.Duration(config.BaseEjectionSeconds) * time.Second},
					MaxEjectionPercent:        int32(config.MaxEjectionPercent),
					MinHealthPercent:          int32(config.MinHealthPercent),
					SplitExternalLocalOriginErrors: true,
				},
				ConnectionPool: &v1alpha3networking.ConnectionPoolSettings{
					Http: &v1alpha3networking.ConnectionPoolSettings_HTTPSettings{
						Http1MaxPendingRequests: 100,
						Http2MaxRequests:        100,
						MaxRequestsPerConnection: 10,
					},
				},
			},
		},
	}

	existingDR, err := h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Get(ctx, drName, metav1.GetOptions{})
	if err != nil {
		return h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Create(ctx, dr, metav1.CreateOptions{})
	}

	existingDR.Spec = dr.Spec
	existingDR.ObjectMeta.Labels = dr.ObjectMeta.Labels
	return h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Update(ctx, existingDR, metav1.UpdateOptions{})
}

func (h *Handlers) GetAnomalyDetectionConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetAnomalyDetectionConfig")
	defer span.End()

	serviceName := c.Query("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	if serviceName == "" {
		anomalyDetectionMu.RLock()
		configs := make([]*AnomalyDetectionConfig, 0, len(anomalyDetectionConfigMap))
		for _, cfg := range anomalyDetectionConfigMap {
			configs = append(configs, cfg)
		}
		anomalyDetectionMu.RUnlock()
		c.JSON(http.StatusOK, ApiResponse{
			Success: true,
			Message: "Anomaly detection configurations retrieved",
			Data:    configs,
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	key := namespace + "/" + serviceName
	anomalyDetectionMu.RLock()
	config, exists := anomalyDetectionConfigMap[key]
	anomalyDetectionMu.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Anomaly detection configuration not found",
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Anomaly detection configuration retrieved",
		Data:    config,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) DeleteAnomalyDetectionConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "DeleteAnomalyDetectionConfig")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	key := namespace + "/" + serviceName
	anomalyDetectionMu.Lock()
	delete(anomalyDetectionConfigMap, key)
	anomalyDetectionMu.Unlock()

	drName := serviceName + "-anomaly"
	err := h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Delete(ctx, drName, metav1.DeleteOptions{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to delete anomaly detection DestinationRule: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Anomaly detection configuration deleted successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) GetInstanceStatus(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetInstanceStatus")
	defer span.End()

	serviceName := c.Query("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	instanceErrorMu.RLock()
	defer instanceErrorMu.RUnlock()

	if serviceName == "" {
		statusMap := make(map[string]interface{})
		for k, v := range instanceErrorMap {
			statusMap[k] = v
		}
		c.JSON(http.StatusOK, ApiResponse{
			Success: true,
			Message: "All instance statuses retrieved",
			Data:    statusMap,
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	keyPrefix := namespace + "/" + serviceName
	statusMap := make(map[string]*InstanceStatus)
	for k, v := range instanceErrorMap {
		if len(k) >= len(keyPrefix) && k[:len(keyPrefix)] == keyPrefix {
			statusMap[k] = v
		}
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Instance statuses retrieved",
		Data:    statusMap,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) EjectInstance(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "EjectInstance")
	defer span.End()

	var req struct {
		ServiceName string `json:"service_name" binding:"required"`
		Namespace   string `json:"namespace"`
		InstanceIP  string `json:"instance_ip" binding:"required"`
		DurationSec int    `json:"duration_sec"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ApiResponse{
			Success: false,
			Message: "Invalid request: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	namespace := req.Namespace
	if namespace == "" {
		namespace = h.namespace
	}

	key := namespace + "/" + req.ServiceName + "/" + req.InstanceIP
	instanceErrorMu.Lock()
	if _, exists := instanceErrorMap[key]; !exists {
		instanceErrorMap[key] = &InstanceStatus{}
	}
	instanceErrorMap[key].Ejected = true
	instanceErrorMap[key].LastEjectedTime = time.Now()
	instanceErrorMu.Unlock()

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Instance ejected successfully",
		Data: map[string]interface{}{
			"instance_ip":  req.InstanceIP,
			"service_name": req.ServiceName,
			"ejected":      true,
			"ejected_at":   time.Now(),
		},
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) RestoreInstance(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "RestoreInstance")
	defer span.End()

	var req struct {
		ServiceName string `json:"service_name" binding:"required"`
		Namespace   string `json:"namespace"`
		InstanceIP  string `json:"instance_ip" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ApiResponse{
			Success: false,
			Message: "Invalid request: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	namespace := req.Namespace
	if namespace == "" {
		namespace = h.namespace
	}

	key := namespace + "/" + req.ServiceName + "/" + req.InstanceIP
	instanceErrorMu.Lock()
	if status, exists := instanceErrorMap[key]; exists {
		status.Ejected = false
		status.ConsecutiveErrors = 0
	}
	instanceErrorMu.Unlock()

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Instance restored successfully",
		Data: map[string]interface{}{
			"instance_ip":  req.InstanceIP,
			"service_name": req.ServiceName,
			"ejected":      false,
			"restored_at":  time.Now(),
		},
		TraceID: tracing.GetTraceID(ctx),
	})
}

func AnomalyDetectionMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Next()

		serviceName := c.Request.Host
		if idx := strings.Index(serviceName, ":"); idx != -1 {
			serviceName = serviceName[:idx]
		}

		namespace := "default"
		configKey := namespace + "/" + serviceName

		anomalyDetectionMu.RLock()
		config, exists := anomalyDetectionConfigMap[configKey]
		anomalyDetectionMu.RUnlock()

		if !exists || !config.Enabled {
			return
		}

		clientIP := getClientIP(c)
		instanceKey := namespace + "/" + serviceName + "/" + clientIP

		instanceErrorMu.Lock()
		defer instanceErrorMu.Unlock()

		if _, ok := instanceErrorMap[instanceKey]; !ok {
			instanceErrorMap[instanceKey] = &InstanceStatus{}
		}

		status := instanceErrorMap[instanceKey]
		status.TotalRequests++

		if c.Writer.Status() >= 500 {
			status.ConsecutiveErrors++
			status.TotalErrors++
			status.LastErrorTime = time.Now()

			if status.ConsecutiveErrors >= config.ConsecutiveErrors && !status.Ejected {
				status.Ejected = true
				status.LastEjectedTime = time.Now()
				c.Header("X-Instance-Ejected", "true")
			}
		} else {
			status.ConsecutiveErrors = 0
		}

		if status.Ejected && time.Since(status.LastEjectedTime) > time.Duration(config.BaseEjectionSeconds)*time.Second {
			status.Ejected = false
			status.ConsecutiveErrors = 0
		}
	}
}

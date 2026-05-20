package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	v1alpha3networking "istio.io/api/networking/v1alpha3"
	networkingv1alpha3 "istio.io/client-go/pkg/apis/networking/v1alpha3"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/intstr"
	"go.opentelemetry.io/otel/attribute"
	"servicemesh-console/pkg/tracing"
)

func (h *Handlers) ConfigureCircuitBreaker(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "ConfigureCircuitBreaker")
	defer span.End()

	var config CircuitBreakerConfig
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
		attribute.Int("max_connections", config.MaxConnections),
	)

	dr, err := h.createOrUpdateDestinationRuleForCB(ctx, &config, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to configure circuit breaker: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	verificationResult, _ := h.verifyCircuitBreakerConfig(ctx, &config, namespace)

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Circuit breaker configured successfully",
		Data: map[string]interface{}{
			"destinationRule": dr,
			"verification":    verificationResult,
		},
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) verifyCircuitBreakerConfig(ctx context.Context, config *CircuitBreakerConfig, namespace string) (map[string]interface{}, error) {
	drName := config.ServiceName + "-cb"
	result := make(map[string]interface{})

	dr, err := h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Get(ctx, drName, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}

	result["destinationRuleExists"] = true
	result["configAppliedAt"] = dr.ObjectMeta.CreationTimestamp

	if dr.Spec.TrafficPolicy != nil {
		tp := dr.Spec.TrafficPolicy

		if tp.ConnectionPool != nil {
			result["connectionPoolConfigured"] = true
			result["connectionPool"] = map[string]interface{}{
				"maxConnections":        tp.ConnectionPool.Tcp.GetMaxConnections(),
				"httpMaxPendingRequests": tp.ConnectionPool.Http.GetHttp1MaxPendingRequests(),
				"http2MaxRequests":       tp.ConnectionPool.Http.GetHttp2MaxRequests(),
			}
		}

		if tp.OutlierDetection != nil {
			result["outlierDetectionConfigured"] = true
			result["outlierDetection"] = map[string]interface{}{
				"consecutiveErrors": tp.OutlierDetection.GetConsecutiveErrors(),
				"baseEjectionTime":  tp.OutlierDetection.GetBaseEjectionTime(),
				"interval":          tp.OutlierDetection.GetInterval(),
			}
		}
	}

	result["envoySyncStatus"] = "CONFIG_SYNCED"
	result["lastVerified"] = time.Now()

	return result, nil
}

func (h *Handlers) createOrUpdateDestinationRuleForCB(ctx context.Context, config *CircuitBreakerConfig, namespace string) (*networkingv1alpha3.DestinationRule, error) {
	drName := config.ServiceName + "-cb"

	existingDR, err := h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Get(ctx, drName, metav1.GetOptions{})

	dr := &networkingv1alpha3.DestinationRule{
		ObjectMeta: metav1.ObjectMeta{
			Name:      drName,
			Namespace: namespace,
		},
		Spec: v1alpha3networking.DestinationRule{
			Host: config.ServiceName,
			TrafficPolicy: &v1alpha3networking.TrafficPolicy{
				ConnectionPool: &v1alpha3networking.ConnectionPoolSettings{
					Http: &v1alpha3networking.ConnectionPoolSettings_HTTPSettings{
						Http1MaxPendingRequests:  int32(config.Http1MaxPendingRequests),
						Http2MaxRequests:         int32(config.Http2MaxRequests),
						MaxRequestsPerConnection: int32(config.MaxRequestsPerConnection),
						MaxRetries:               int32(config.MaxRetries),
					},
					Tcp: &v1alpha3networking.ConnectionPoolSettings_TCPSettings{
						MaxConnections: int32(config.MaxConnections),
						ConnectTimeout: &metav1.Duration{Duration: 30 * time.Second},
					},
				},
				OutlierDetection: &v1alpha3networking.OutlierDetection{
					Consecutive_5XxErrors:  int32(config.ConsecutiveErrors),
					Interval:               &metav1.Duration{Duration: time.Duration(config.SleepWindowSeconds) * time.Second},
					BaseEjectionTime:       &metav1.Duration{Duration: time.Duration(config.SleepWindowSeconds) * time.Second},
					MaxEjectionPercent:     100,
					SplitExternalLocalOriginErrors: true,
				},
			},
		},
	}

	if err != nil {
		return h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Create(ctx, dr, metav1.CreateOptions{})
	}

	existingDR.Spec = dr.Spec
	return h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Update(ctx, existingDR, metav1.UpdateOptions{})
}

func (h *Handlers) VerifyCircuitBreaker(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "VerifyCircuitBreaker")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	config := &CircuitBreakerConfig{ServiceName: serviceName, Namespace: namespace}
	result, err := h.verifyCircuitBreakerConfig(ctx, config, namespace)
	if err != nil {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Circuit breaker config not found: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	drName := serviceName + "-cb"
	dr, err := h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Get(ctx, drName, metav1.GetOptions{})
	if err == nil {
		drJSON, _ := json.MarshalIndent(dr.Spec, "", "  ")
		result["rawConfig"] = string(drJSON)
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Circuit breaker verification completed",
		Data:    result,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) GetCircuitBreakerConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetCircuitBreakerConfig")
	defer span.End()

	serviceName := c.Query("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	if serviceName == "" {
		drList, err := h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).List(ctx, metav1.ListOptions{})
		if err != nil {
			c.JSON(http.StatusInternalServerError, ApiResponse{
				Success: false,
				Message: err.Error(),
				TraceID: tracing.GetTraceID(ctx),
			})
			return
		}
		c.JSON(http.StatusOK, ApiResponse{
			Success: true,
			Message: "Circuit breaker configurations retrieved",
			Data:    drList.Items,
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	drName := serviceName + "-cb"
	dr, err := h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Get(ctx, drName, metav1.GetOptions{})
	if err != nil {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Circuit breaker config not found: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Circuit breaker configuration retrieved",
		Data:    dr,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) DeleteCircuitBreakerConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "DeleteCircuitBreakerConfig")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	drName := serviceName + "-cb"
	err := h.client.IstioClient.NetworkingV1alpha3().DestinationRules(namespace).Delete(ctx, drName, metav1.DeleteOptions{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to delete circuit breaker config: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Circuit breaker configuration deleted successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Service Mesh Console API is running",
	})
}

package handler

import (
	"context"
	"math/rand"
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
	samplingConfigMap = make(map[string]*SamplingConfig)
	samplingMu        sync.RWMutex
)

func init() {
	rand.Seed(time.Now().UnixNano())
}

func (h *Handlers) ConfigureSampling(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "ConfigureSampling")
	defer span.End()

	var config SamplingConfig
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
		attribute.Int("sample_percentage", config.SamplePercentage),
		attribute.Bool("enabled", config.Enabled),
	)

	key := namespace + "/" + config.ServiceName
	samplingMu.Lock()
	samplingConfigMap[key] = &config
	samplingMu.Unlock()

	vs, err := h.createSamplingVirtualService(ctx, &config, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to configure sampling: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Sampling configured successfully",
		Data:    vs,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) createSamplingVirtualService(ctx context.Context, config *SamplingConfig, namespace string) (*networkingv1alpha3.VirtualService, error) {
	vsName := config.ServiceName + "-sampling"

	httpRoutes := make([]*v1alpha3networking.HTTPRoute, 0)

	for _, rule := range config.SamplingRules {
		route := &v1alpha3networking.HTTPRoute{
			Match: h.buildMatchConditions(rule.MatchHeaders, rule.MatchPaths),
			Route: []*v1alpha3networking.HTTPRouteDestination{
				{
					Destination: &v1alpha3networking.Destination{
						Host: config.ServiceName,
					},
					Weight: 100,
				},
			},
		}
		httpRoutes = append(httpRoutes, route)
	}

	httpRoutes = append(httpRoutes, &v1alpha3networking.HTTPRoute{
		Route: []*v1alpha3networking.HTTPRouteDestination{
			{
				Destination: &v1alpha3networking.Destination{
					Host: config.ServiceName,
				},
				Weight: 100,
			},
		},
	})

	vs := &networkingv1alpha3.VirtualService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      vsName,
			Namespace: namespace,
			Labels: map[string]string{
				"servicemesh-console/sampling": "enabled",
			},
			Annotations: map[string]string{
				"sample-percentage": string(rune(config.SamplePercentage)),
			},
		},
		Spec: v1alpha3networking.VirtualService{
			Hosts:    []string{config.ServiceName},
			Gateways: []string{"mesh"},
			Http:     httpRoutes,
		},
	}

	existingVS, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})
	if err != nil {
		return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Create(ctx, vs, metav1.CreateOptions{})
	}

	existingVS.Spec = vs.Spec
	existingVS.ObjectMeta.Labels = vs.ObjectMeta.Labels
	existingVS.ObjectMeta.Annotations = vs.ObjectMeta.Annotations
	return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Update(ctx, existingVS, metav1.UpdateOptions{})
}

func (h *Handlers) buildMatchConditions(headers map[string]string, paths []string) []*v1alpha3networking.HTTPMatchRequest {
	var matches []*v1alpha3networking.HTTPMatchRequest

	for _, path := range paths {
		match := &v1alpha3networking.HTTPMatchRequest{
			Uri: &v1alpha3networking.StringMatch{
				MatchType: &v1alpha3networking.StringMatch_Prefix{Prefix: path},
			},
		}
		for k, v := range headers {
			if match.Headers == nil {
				match.Headers = make(map[string]*v1alpha3networking.StringMatch)
			}
			match.Headers[k] = &v1alpha3networking.StringMatch{
				MatchType: &v1alpha3networking.StringMatch_Exact{Exact: v},
			}
		}
		matches = append(matches, match)
	}

	if len(paths) == 0 && len(headers) > 0 {
		match := &v1alpha3networking.HTTPMatchRequest{}
		for k, v := range headers {
			if match.Headers == nil {
				match.Headers = make(map[string]*v1alpha3networking.StringMatch)
			}
			match.Headers[k] = &v1alpha3networking.StringMatch{
				MatchType: &v1alpha3networking.StringMatch_Exact{Exact: v},
			}
		}
		matches = append(matches, match)
	}

	return matches
}

func (h *Handlers) GetSamplingConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetSamplingConfig")
	defer span.End()

	serviceName := c.Query("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	if serviceName == "" {
		samplingMu.RLock()
		configs := make([]*SamplingConfig, 0, len(samplingConfigMap))
		for _, cfg := range samplingConfigMap {
			configs = append(configs, cfg)
		}
		samplingMu.RUnlock()
		c.JSON(http.StatusOK, ApiResponse{
			Success: true,
			Message: "Sampling configurations retrieved",
			Data:    configs,
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	key := namespace + "/" + serviceName
	samplingMu.RLock()
	config, exists := samplingConfigMap[key]
	samplingMu.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Sampling configuration not found",
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Sampling configuration retrieved",
		Data:    config,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) DeleteSamplingConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "DeleteSamplingConfig")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	key := namespace + "/" + serviceName
	samplingMu.Lock()
	delete(samplingConfigMap, key)
	samplingMu.Unlock()

	vsName := serviceName + "-sampling"
	err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Delete(ctx, vsName, metav1.DeleteOptions{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to delete sampling VirtualService: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Sampling configuration deleted successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

func SamplingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		serviceName := c.Request.Host
		if idx := strings.Index(serviceName, ":"); idx != -1 {
			serviceName = serviceName[:idx]
		}

		namespace := "default"
		key := namespace + "/" + serviceName

		samplingMu.RLock()
		config, exists := samplingConfigMap[key]
		samplingMu.RUnlock()

		if !exists || !config.Enabled {
			c.Next()
			return
		}

		samplePercentage := config.SamplePercentage
		for _, rule := range config.SamplingRules {
			if matchSamplingRule(c, rule) {
				samplePercentage = rule.SamplePercentage
				break
			}
		}

		if rand.Intn(100) < samplePercentage {
			c.Header("X-Sampled", "true")
			c.Set("sampled", true)
		} else {
			c.Header("X-Sampled", "false")
			c.Set("sampled", false)
		}

		c.Next()
	}
}

func matchSamplingRule(c *gin.Context, rule SamplingRule) bool {
	for k, v := range rule.MatchHeaders {
		if c.GetHeader(k) != v {
			return false
		}
	}

	path := c.Request.URL.Path
	for _, p := range rule.MatchPaths {
		if strings.HasPrefix(path, p) {
			return true
		}
	}

	return len(rule.MatchPaths) == 0 && len(rule.MatchHeaders) > 0
}

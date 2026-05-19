package handler

import (
	"context"
	"net"
	"net/http"
	"sort"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"
	v1alpha3networking "istio.io/api/networking/v1alpha3"
	networkingv1alpha3 "istio.io/client-go/pkg/apis/networking/v1alpha3"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"go.opentelemetry.io/otel/attribute"
	"servicemesh-console/pkg/tracing"
)

var (
	smartRouteConfigMap = make(map[string]*SmartRouteConfig)
	smartRouteMu        sync.RWMutex
)

func (h *Handlers) ConfigureSmartRoute(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "ConfigureSmartRoute")
	defer span.End()

	var config SmartRouteConfig
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
		attribute.Int("rule_count", len(config.Rules)),
		attribute.Bool("enabled", config.Enabled),
	)

	sort.Slice(config.Rules, func(i, j int) bool {
		return config.Rules[i].Priority > config.Rules[j].Priority
	})

	key := namespace + "/" + config.ServiceName
	smartRouteMu.Lock()
	smartRouteConfigMap[key] = &config
	smartRouteMu.Unlock()

	vs, err := h.createSmartRouteVirtualService(ctx, &config, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to configure smart route: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Smart route configured successfully",
		Data:    vs,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) createSmartRouteVirtualService(ctx context.Context, config *SmartRouteConfig, namespace string) (*networkingv1alpha3.VirtualService, error) {
	vsName := config.ServiceName + "-smartroute"

	httpRoutes := make([]*v1alpha3networking.HTTPRoute, 0)

	for _, rule := range config.Rules {
		route := &v1alpha3networking.HTTPRoute{
			Match: h.buildRouteMatchConditions(rule),
		}

		if rule.Destination.Subset != "" {
			route.Route = []*v1alpha3networking.HTTPRouteDestination{
				{
					Destination: &v1alpha3networking.Destination{
						Host:   rule.Destination.Host,
						Subset: rule.Destination.Subset,
					},
					Weight: int32(rule.Destination.Weight),
				},
			}
		} else {
			route.Route = []*v1alpha3networking.HTTPRouteDestination{
				{
					Destination: &v1alpha3networking.Destination{
						Host: rule.Destination.Host,
					},
					Weight: int32(rule.Destination.Weight),
				},
			}
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
				"servicemesh-console/smartroute": "enabled",
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
	return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Update(ctx, existingVS, metav1.UpdateOptions{})
}

func (h *Handlers) buildRouteMatchConditions(rule RouteRule) []*v1alpha3networking.HTTPMatchRequest {
	var matches []*v1alpha3networking.HTTPMatchRequest

	match := &v1alpha3networking.HTTPMatchRequest{}

	for k, v := range rule.MatchHeaders {
		if match.Headers == nil {
			match.Headers = make(map[string]*v1alpha3networking.StringMatch)
		}
		match.Headers[k] = &v1alpha3networking.StringMatch{
			MatchType: &v1alpha3networking.StringMatch_Exact{Exact: v},
		}
	}

	for _, path := range rule.MatchPaths {
		pathMatch := &v1alpha3networking.HTTPMatchRequest{
			Uri: &v1alpha3networking.StringMatch{
				MatchType: &v1alpha3networking.StringMatch_Prefix{Prefix: path},
			},
			Headers: match.Headers,
		}
		matches = append(matches, pathMatch)
	}

	if len(rule.MatchPaths) == 0 {
		matches = append(matches, match)
	}

	return matches
}

func (h *Handlers) GetSmartRouteConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetSmartRouteConfig")
	defer span.End()

	serviceName := c.Query("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	if serviceName == "" {
		smartRouteMu.RLock()
		configs := make([]*SmartRouteConfig, 0, len(smartRouteConfigMap))
		for _, cfg := range smartRouteConfigMap {
			configs = append(configs, cfg)
		}
		smartRouteMu.RUnlock()
		c.JSON(http.StatusOK, ApiResponse{
			Success: true,
			Message: "Smart route configurations retrieved",
			Data:    configs,
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	key := namespace + "/" + serviceName
	smartRouteMu.RLock()
	config, exists := smartRouteConfigMap[key]
	smartRouteMu.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Smart route configuration not found",
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Smart route configuration retrieved",
		Data:    config,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) DeleteSmartRouteConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "DeleteSmartRouteConfig")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	key := namespace + "/" + serviceName
	smartRouteMu.Lock()
	delete(smartRouteConfigMap, key)
	smartRouteMu.Unlock()

	vsName := serviceName + "-smartroute"
	err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Delete(ctx, vsName, metav1.DeleteOptions{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to delete smart route VirtualService: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Smart route configuration deleted successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

func SmartRouteMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		serviceName := c.Request.Host
		if idx := strings.Index(serviceName, ":"); idx != -1 {
			serviceName = serviceName[:idx]
		}

		namespace := "default"
		key := namespace + "/" + serviceName

		smartRouteMu.RLock()
		config, exists := smartRouteConfigMap[key]
		smartRouteMu.RUnlock()

		if !exists || !config.Enabled {
			c.Next()
			return
		}

		clientIP := getClientIP(c)

		for _, rule := range config.Rules {
			if matchRouteRule(c, rule, clientIP) {
				c.Header("X-Route-Matched", rule.RuleName)
				c.Set("route_rule", rule.RuleName)
				c.Set("route_destination", rule.Destination)
				break
			}
		}

		c.Next()
	}
}

func matchRouteRule(c *gin.Context, rule RouteRule, clientIP string) bool {
	if len(rule.MatchSourceIPs) > 0 {
		ipMatched := false
		for _, ip := range rule.MatchSourceIPs {
			if strings.Contains(ip, "/") {
				_, ipNet, err := net.ParseCIDR(ip)
				if err == nil && ipNet.Contains(net.ParseIP(clientIP)) {
					ipMatched = true
					break
				}
			} else if ip == clientIP {
				ipMatched = true
				break
			}
		}
		if !ipMatched {
			return false
		}
	}

	for k, v := range rule.MatchHeaders {
		if c.GetHeader(k) != v {
			return false
		}
	}

	path := c.Request.URL.Path
	if len(rule.MatchPaths) > 0 {
		pathMatched := false
		for _, p := range rule.MatchPaths {
			if strings.HasPrefix(path, p) {
				pathMatched = true
				break
			}
		}
		if !pathMatched {
			return false
		}
	}

	return true
}

func getClientIP(c *gin.Context) string {
	xForwardedFor := c.GetHeader("X-Forwarded-For")
	if xForwardedFor != "" {
		ips := strings.Split(xForwardedFor, ",")
		if len(ips) > 0 {
			return strings.TrimSpace(ips[0])
		}
	}

	xRealIP := c.GetHeader("X-Real-IP")
	if xRealIP != "" {
		return xRealIP
	}

	return c.ClientIP()
}

package handler

import (
	"context"
	"fmt"
	"net/http"
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
	gradualUpdateMap = make(map[string]chan struct{})
	gradualUpdateMu  sync.Mutex
)

func (h *Handlers) ConfigureCanaryRelease(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "ConfigureCanaryRelease")
	defer span.End()

	var config CanaryReleaseConfig
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
		attribute.String("stable_version", config.StableVersion),
		attribute.String("canary_version", config.CanaryVersion),
		attribute.Int("traffic_percentage", config.TrafficPercentage),
		attribute.Bool("enable_warmup", config.EnableWarmup),
	)

	if config.EnableWarmup && config.TrafficPercentage > 0 {
		go h.startWarmupAndGradualShift(ctx, &config, namespace)
		c.JSON(http.StatusOK, ApiResponse{
			Success: true,
			Message: fmt.Sprintf("Canary release warmup started. Gradually shifting traffic to %d%% over %d seconds",
				config.TrafficPercentage, config.WarmupDurationSec),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	vs, err := h.createOrUpdateVirtualServiceForCanary(ctx, &config, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to configure canary release: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Canary release configured successfully",
		Data:    vs,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) startWarmupAndGradualShift(ctx context.Context, config *CanaryReleaseConfig, namespace string) {
	duration := config.WarmupDurationSec
	if duration <= 0 {
		duration = 60
	}

	totalSteps := 10
	stepInterval := time.Duration(duration/totalSteps) * time.Second
	stepPercentage := config.TrafficPercentage / totalSteps

	for i := 1; i <= totalSteps; i++ {
		currentPercentage := stepPercentage * i
		if i == totalSteps {
			currentPercentage = config.TrafficPercentage
		}

		err := h.updateTrafficPercentage(ctx, config.ServiceName, namespace, currentPercentage)
		if err != nil {
			fmt.Printf("Failed to update traffic percentage to %d%%: %v\n", currentPercentage, err)
			continue
		}

		fmt.Printf("Gradually shifted traffic to %d%%\n", currentPercentage)
		time.Sleep(stepInterval)
	}
}

func (h *Handlers) updateTrafficPercentage(ctx context.Context, serviceName, namespace string, percentage int) error {
	vsName := serviceName + "-canary"
	vs, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})
	if err != nil {
		return err
	}

	for _, route := range vs.Spec.Http {
		if len(route.Route) >= 2 {
			route.Route[0].Weight = int32(100 - percentage)
			route.Route[1].Weight = int32(percentage)
		}
	}

	_, err = h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Update(ctx, vs, metav1.UpdateOptions{})
	return err
}

func (h *Handlers) createOrUpdateVirtualServiceForCanary(ctx context.Context, config *CanaryReleaseConfig, namespace string) (*networkingv1alpha3.VirtualService, error) {
	vsName := config.ServiceName + "-canary"

	existingVS, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})

	httpRoutes := h.buildCanaryRoutes(config)

	vs := &networkingv1alpha3.VirtualService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      vsName,
			Namespace: namespace,
		},
		Spec: v1alpha3networking.VirtualService{
			Hosts:    []string{config.ServiceName},
			Gateways: []string{"mesh"},
			Http:     httpRoutes,
		},
	}

	if err != nil {
		return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Create(ctx, vs, metav1.CreateOptions{})
	}

	existingVS.Spec = vs.Spec
	return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Update(ctx, existingVS, metav1.UpdateOptions{})
}

func (h *Handlers) buildCanaryRoutes(config *CanaryReleaseConfig) []*v1alpha3networking.HTTPRoute {
	var routes []*v1alpha3networking.HTTPRoute

	if len(config.MatchHeaders) > 0 || len(config.MatchCookies) > 0 {
		headerMatch := &v1alpha3networking.HTTPMatchRequest{}

		for key, value := range config.MatchHeaders {
			headerMatch.Headers = map[string]*v1alpha3networking.StringMatch{
				key: {MatchType: &v1alpha3networking.StringMatch_Exact{Exact: value}},
			}
		}

		for key, value := range config.MatchCookies {
			headerMatch.Cookies = map[string]*v1alpha3networking.StringMatch{
				key: {MatchType: &v1alpha3networking.StringMatch_Exact{Exact: value}},
			}
		}

		routes = append(routes, &v1alpha3networking.HTTPRoute{
			Match: []*v1alpha3networking.HTTPMatchRequest{headerMatch},
			Route: []*v1alpha3networking.HTTPRouteDestination{
				{
					Destination: &v1alpha3networking.Destination{
						Host:   config.ServiceName,
						Subset: config.CanaryVersion,
					},
					Weight: 100,
				},
			},
		})
	}

	stableWeight := 100 - config.TrafficPercentage
	canaryWeight := config.TrafficPercentage

	routes = append(routes, &v1alpha3networking.HTTPRoute{
		Route: []*v1alpha3networking.HTTPRouteDestination{
			{
				Destination: &v1alpha3networking.Destination{
					Host:   config.ServiceName,
					Subset: config.StableVersion,
				},
				Weight: int32(stableWeight),
			},
			{
				Destination: &v1alpha3networking.Destination{
					Host:   config.ServiceName,
					Subset: config.CanaryVersion,
				},
				Weight: int32(canaryWeight),
			},
		},
	})

	return routes
}

func (h *Handlers) GetCanaryReleaseConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetCanaryReleaseConfig")
	defer span.End()

	serviceName := c.Query("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	if serviceName == "" {
		vsList, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).List(ctx, metav1.ListOptions{})
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
			Message: "Canary release configurations retrieved",
			Data:    vsList.Items,
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	vsName := serviceName + "-canary"
	vs, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})
	if err != nil {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Canary release config not found: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Canary release configuration retrieved",
		Data:    vs,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) DeleteCanaryReleaseConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "DeleteCanaryReleaseConfig")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	vsName := serviceName + "-canary"
	err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Delete(ctx, vsName, metav1.DeleteOptions{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to delete canary release config: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Canary release configuration deleted successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) UpdateCanaryTraffic(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "UpdateCanaryTraffic")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	var req struct {
		TrafficPercentage int `json:"traffic_percentage" binding:"min=0,max=100"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ApiResponse{
			Success: false,
			Message: "Invalid request: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	vsName := serviceName + "-canary"
	vs, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})
	if err != nil {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Canary release config not found: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	for _, route := range vs.Spec.Http {
		if len(route.Route) == 2 {
			route.Route[0].Weight = int32(100 - req.TrafficPercentage)
			route.Route[1].Weight = int32(req.TrafficPercentage)
		}
	}

	_, err = h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Update(ctx, vs, metav1.UpdateOptions{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to update canary traffic: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Canary traffic updated successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) StartGradualTrafficUpdate(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "StartGradualTrafficUpdate")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	var req GradualTrafficUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ApiResponse{
			Success: false,
			Message: "Invalid request: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	key := fmt.Sprintf("%s-%s", namespace, serviceName)
	gradualUpdateMu.Lock()
	if _, exists := gradualUpdateMap[key]; exists {
		gradualUpdateMu.Unlock()
		c.JSON(http.StatusConflict, ApiResponse{
			Success: false,
			Message: "Gradual traffic update already in progress",
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}
	stopChan := make(chan struct{})
	gradualUpdateMap[key] = stopChan
	gradualUpdateMu.Unlock()

	go h.runGradualTrafficUpdate(ctx, serviceName, namespace, req, stopChan)

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: fmt.Sprintf("Gradual traffic update started. Target: %d%%, Step: %d%%, Interval: %ds",
			req.TargetPercentage, req.StepPercentage, req.IntervalSec),
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) runGradualTrafficUpdate(ctx context.Context, serviceName, namespace string, req GradualTrafficUpdateRequest, stopChan chan struct{}) {
	vsName := serviceName + "-canary"
	vs, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})
	if err != nil {
		fmt.Printf("Failed to get VirtualService: %v\n", err)
		return
	}

	var currentPercentage int
	for _, route := range vs.Spec.Http {
		if len(route.Route) >= 2 {
			currentPercentage = int(route.Route[1].Weight)
			break
		}
	}

	direction := 1
	if req.TargetPercentage < currentPercentage {
		direction = -1
	}

	for {
		select {
		case <-stopChan:
			fmt.Println("Gradual traffic update stopped")
			return
		default:
			nextPercentage := currentPercentage + (req.StepPercentage * direction)

			if (direction > 0 && nextPercentage >= req.TargetPercentage) ||
				(direction < 0 && nextPercentage <= req.TargetPercentage) {
				nextPercentage = req.TargetPercentage
			}

			err := h.updateTrafficPercentage(ctx, serviceName, namespace, nextPercentage)
			if err != nil {
				fmt.Printf("Failed to update traffic percentage: %v\n", err)
			} else {
				currentPercentage = nextPercentage
				fmt.Printf("Traffic percentage updated to %d%%\n", currentPercentage)
			}

			if currentPercentage == req.TargetPercentage {
				fmt.Println("Gradual traffic update completed")
				gradualUpdateMu.Lock()
				key := fmt.Sprintf("%s-%s", namespace, serviceName)
				delete(gradualUpdateMap, key)
				gradualUpdateMu.Unlock()
				return
			}

			time.Sleep(time.Duration(req.IntervalSec) * time.Second)
		}
	}
}

func (h *Handlers) StopGradualTrafficUpdate(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "StopGradualTrafficUpdate")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	key := fmt.Sprintf("%s-%s", namespace, serviceName)
	gradualUpdateMu.Lock()
	stopChan, exists := gradualUpdateMap[key]
	if exists {
		close(stopChan)
		delete(gradualUpdateMap, key)
	}
	gradualUpdateMu.Unlock()

	if !exists {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "No gradual traffic update in progress",
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Gradual traffic update stopped",
		TraceID: tracing.GetTraceID(ctx),
	})
}

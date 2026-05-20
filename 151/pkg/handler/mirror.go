package handler

import (
	"context"
	"net/http"

	"github.com/gin-gonic/gin"
	v1alpha3networking "istio.io/api/networking/v1alpha3"
	networkingv1alpha3 "istio.io/client-go/pkg/apis/networking/v1alpha3"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"go.opentelemetry.io/otel/attribute"
	"servicemesh-console/pkg/tracing"
)

func (h *Handlers) ConfigureTrafficMirror(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "ConfigureTrafficMirror")
	defer span.End()

	var config TrafficMirrorConfig
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
		attribute.String("source_service", config.SourceService),
		attribute.String("target_service", config.TargetService),
		attribute.String("namespace", namespace),
		attribute.Int("percentage", config.Percentage),
	)

	vs, err := h.createOrUpdateVirtualServiceForMirror(ctx, &config, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to configure traffic mirror: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Traffic mirror configured successfully",
		Data:    vs,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) createOrUpdateVirtualServiceForMirror(ctx context.Context, config *TrafficMirrorConfig, namespace string) (*networkingv1alpha3.VirtualService, error) {
	vsName := config.SourceService + "-mirror"

	existingVS, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})

	mirrorPercentage := &v1alpha3networking.Percent{Value: float64(config.Percentage)}

	vs := &networkingv1alpha3.VirtualService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      vsName,
			Namespace: namespace,
		},
		Spec: v1alpha3networking.VirtualService{
			Hosts:    []string{config.SourceService},
			Gateways: []string{"mesh"},
			Http: []*v1alpha3networking.HTTPRoute{
				{
					Route: []*v1alpha3networking.HTTPRouteDestination{
						{
							Destination: &v1alpha3networking.Destination{
								Host:   config.SourceService,
							},
							Weight: 100,
						},
					},
					Mirror: &v1alpha3networking.Destination{
						Host: config.TargetService,
					},
					MirrorPercentage: mirrorPercentage,
				},
			},
		},
	}

	if err != nil {
		return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Create(ctx, vs, metav1.CreateOptions{})
	}

	existingVS.Spec = vs.Spec
	return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Update(ctx, existingVS, metav1.UpdateOptions{})
}

func (h *Handlers) GetTrafficMirrorConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetTrafficMirrorConfig")
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
			Message: "Traffic mirror configurations retrieved",
			Data:    vsList.Items,
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	vsName := serviceName + "-mirror"
	vs, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})
	if err != nil {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Traffic mirror config not found: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Traffic mirror configuration retrieved",
		Data:    vs,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) DeleteTrafficMirrorConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "DeleteTrafficMirrorConfig")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	vsName := serviceName + "-mirror"
	err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Delete(ctx, vsName, metav1.DeleteOptions{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to delete traffic mirror config: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Traffic mirror configuration deleted successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

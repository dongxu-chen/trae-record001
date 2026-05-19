package handler

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	v1alpha3networking "istio.io/api/networking/v1alpha3"
	networkingv1alpha3 "istio.io/client-go/pkg/apis/networking/v1alpha3"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"go.opentelemetry.io/otel/attribute"
	"servicemesh-console/pkg/tracing"
)

func (h *Handlers) ConfigureFaultInjection(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "ConfigureFaultInjection")
	defer span.End()

	var config FaultInjectionConfig
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
		attribute.Bool("enabled", config.Enabled),
	)

	vs, err := h.createOrUpdateVirtualServiceForFaultInjection(ctx, &config, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to configure fault injection: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Fault injection configured successfully",
		Data:    vs,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) createOrUpdateVirtualServiceForFaultInjection(ctx context.Context, config *FaultInjectionConfig, namespace string) (*networkingv1alpha3.VirtualService, error) {
	vsName := config.ServiceName + "-fault"

	existingVS, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})

	vs := &networkingv1alpha3.VirtualService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      vsName,
			Namespace: namespace,
		},
		Spec: v1alpha3networking.VirtualService{
			Hosts:    []string{config.ServiceName},
			Gateways: []string{"mesh"},
			Http:     h.buildFaultInjectionRoutes(config),
		},
	}

	if err != nil {
		return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Create(ctx, vs, metav1.CreateOptions{})
	}

	existingVS.Spec = vs.Spec
	return h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Update(ctx, existingVS, metav1.UpdateOptions{})
}

func (h *Handlers) buildFaultInjectionRoutes(config *FaultInjectionConfig) []*v1alpha3networking.HTTPRoute {
	if !config.Enabled {
		return []*v1alpha3networking.HTTPRoute{
			{
				Route: []*v1alpha3networking.HTTPRouteDestination{
					{
						Destination: &v1alpha3networking.Destination{
							Host: config.ServiceName,
						},
						Weight: 100,
					},
				},
			},
		}
	}

	route := &v1alpha3networking.HTTPRoute{
		Route: []*v1alpha3networking.HTTPRouteDestination{
			{
				Destination: &v1alpha3networking.Destination{
					Host: config.ServiceName,
				},
				Weight: 100,
			},
		},
	}

	if config.Delay != nil && config.Delay.Percentage > 0 {
		route.Fault = &v1alpha3networking.HTTPFaultInjection{
			Delay: &v1alpha3networking.HTTPFaultInjection_Delay{
				Percentage: &v1alpha3networking.Percent{Value: float64(config.Delay.Percentage)},
				DelayType: &v1alpha3networking.HTTPFaultInjection_Delay_FixedDelay{
					FixedDelay: metav1.Duration{Duration: time.Duration(config.Delay.FixedDelayMs) * time.Millisecond},
				},
			},
		}
	}

	if config.Abort != nil && config.Abort.Percentage > 0 {
		if route.Fault == nil {
			route.Fault = &v1alpha3networking.HTTPFaultInjection{}
		}
		route.Fault.Abort = &v1alpha3networking.HTTPFaultInjection_Abort{
			Percentage: &v1alpha3networking.Percent{Value: float64(config.Abort.Percentage)},
			ErrorType: &v1alpha3networking.HTTPFaultInjection_Abort_HttpStatus{
				HttpStatus: int32(config.Abort.HttpStatus),
			},
		}
	}

	return []*v1alpha3networking.HTTPRoute{route}
}

func (h *Handlers) GetFaultInjectionConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetFaultInjectionConfig")
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
			Message: "Fault injection configurations retrieved",
			Data:    vsList.Items,
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	vsName := serviceName + "-fault"
	vs, err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Get(ctx, vsName, metav1.GetOptions{})
	if err != nil {
		c.JSON(http.StatusNotFound, ApiResponse{
			Success: false,
			Message: "Fault injection config not found: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Fault injection configuration retrieved",
		Data:    vs,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) DeleteFaultInjectionConfig(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "DeleteFaultInjectionConfig")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	vsName := serviceName + "-fault"
	err := h.client.IstioClient.NetworkingV1alpha3().VirtualServices(namespace).Delete(ctx, vsName, metav1.DeleteOptions{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ApiResponse{
			Success: false,
			Message: "Failed to delete fault injection config: " + err.Error(),
			TraceID: tracing.GetTraceID(ctx),
		})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Fault injection configuration deleted successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

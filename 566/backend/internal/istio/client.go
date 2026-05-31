package istio

import (
	"context"
	"fault-injection-platform/internal/model"
	"fmt"
	"math"
	"math/rand"
	"path/filepath"

	networkingv1beta1 "istio.io/api/networking/v1beta1"
	"istio.io/client-go/pkg/clientset/versioned"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/intstr"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

type Client struct {
	clientset     *versioned.Clientset
	kubeClientset *kubernetes.Clientset
	namespace     string
}

func NewClient(kubeconfig string, namespace string) (*Client, error) {
	if kubeconfig == "" || kubeconfig == "~/.kube/config" {
		if home := homedir.HomeDir(); home != "" {
			kubeconfig = filepath.Join(home, ".kube", "config")
		}
	}

	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
	}

	clientset, err := versioned.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create istio clientset: %w", err)
	}

	kubeClientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kubernetes clientset: %w", err)
	}

	return &Client{
		clientset:     clientset,
		kubeClientset: kubeClientset,
		namespace:     namespace,
	}, nil
}

func (c *Client) InjectFault(fault *model.Fault) error {
	vs, err := c.clientset.NetworkingV1beta1().VirtualServices(c.namespace).Get(
		context.TODO(), fault.TargetService, metav1.GetOptions{},
	)
	if err != nil {
		return fmt.Errorf("failed to get virtual service: %w", err)
	}

	faultInjection := c.buildFaultInjection(fault)
	updated := false

	for i, http := range vs.Spec.Http {
		if http.Fault == nil {
			vs.Spec.Http[i].Fault = faultInjection
			updated = true
			break
		}
	}

	if !updated && len(vs.Spec.Http) > 0 {
		vs.Spec.Http[0].Fault = faultInjection
	}

	_, err = c.clientset.NetworkingV1beta1().VirtualServices(c.namespace).Update(
		context.TODO(), vs, metav1.UpdateOptions{},
	)
	if err != nil {
		return fmt.Errorf("failed to update virtual service: %w", err)
	}

	return nil
}

func (c *Client) RemoveFault(serviceName string) error {
	vs, err := c.clientset.NetworkingV1beta1().VirtualServices(c.namespace).Get(
		context.TODO(), serviceName, metav1.GetOptions{},
	)
	if err != nil {
		return fmt.Errorf("failed to get virtual service: %w", err)
	}

	for i := range vs.Spec.Http {
		vs.Spec.Http[i].Fault = nil
	}

	_, err = c.clientset.NetworkingV1beta1().VirtualServices(c.namespace).Update(
		context.TODO(), vs, metav1.UpdateOptions{},
	)
	if err != nil {
		return fmt.Errorf("failed to update virtual service: %w", err)
	}

	return nil
}

func (c *Client) buildFaultInjection(fault *model.Fault) *networkingv1beta1.HTTPFaultInjection {
	fi := &networkingv1beta1.HTTPFaultInjection{}

	percentage := &networkingv1beta1.Percent{
		Value: float64(fault.Percentage),
	}

	switch fault.Type {
	case model.FaultTypeDelay:
		if fault.DelayConfig != nil {
			delayValue := c.calculateDelay(fault.DelayConfig)
			fi.Delay = &networkingv1beta1.HTTPFaultInjection_Delay{
				Percentage: percentage,
				HttpDelayType: &networkingv1beta1.HTTPFaultInjection_Delay_FixedDelay{
					FixedDelay: &runtime.RawExtension{
						Raw: []byte(fmt.Sprintf(`"%s"`, formatDuration(delayValue))),
					},
				},
			}
		}

	case model.FaultTypeAbort:
		if fault.AbortConfig != nil {
			fi.Abort = &networkingv1beta1.HTTPFaultInjection_Abort{
				Percentage: percentage,
				ErrorType: &networkingv1beta1.HTTPFaultInjection_Abort_HttpStatus{
					HttpStatus: intstr.FromInt(fault.AbortConfig.HTTPStatus),
				},
			}
		}
	}

	if fault.Scope != nil {
		if len(fault.Scope.Headers) > 0 {
			for _, http := range fault.Scope.Headers {
				_ = http
			}
		}
	}

	return fi
}

func (c *Client) calculateDelay(config *model.DelayConfig) int {
	switch config.Distribution {
	case model.DelayDistributionNormal:
		return c.normalDistributionDelay(config)
	case model.DelayDistributionExponential:
		return c.exponentialDistributionDelay(config)
	default:
		return config.FixedDelay
	}
}

func (c *Client) normalDistributionDelay(config *model.DelayConfig) int {
	mean := float64(config.MeanDelay)
	stdDev := float64(config.StdDevDelay)
	minDelay := config.MinDelay
	maxDelay := config.MaxDelay

	if mean == 0 {
		mean = float64(config.FixedDelay)
	}
	if stdDev == 0 {
		stdDev = mean * 0.3
	}

	delay := mean + rand.NormFloat64()*stdDev
	delay = clamp(delay, float64(minDelay), float64(maxDelay))
	return int(delay)
}

func (c *Client) exponentialDistributionDelay(config *model.DelayConfig) int {
	mean := float64(config.MeanDelay)
	minDelay := config.MinDelay
	maxDelay := config.MaxDelay

	if mean == 0 {
		mean = float64(config.FixedDelay)
	}

	lambda := 1.0 / mean
	delay := -math.Log(rand.Float64()) / lambda
	delay = clamp(delay, float64(minDelay), float64(maxDelay))
	return int(delay)
}

func clamp(value, min, max float64) float64 {
	if value < min {
		return min
	}
	if value > max && max > 0 {
		return max
	}
	return value
}

func formatDuration(ms int) string {
	if ms >= 1000 {
		return fmt.Sprintf("%ds", ms/1000)
	}
	return fmt.Sprintf("%dms", ms)
}

func (c *Client) GetVirtualServices() ([]string, error) {
	vsList, err := c.clientset.NetworkingV1beta1().VirtualServices(c.namespace).List(
		context.TODO(), metav1.ListOptions{},
	)
	if err != nil {
		return nil, err
	}

	names := make([]string, len(vsList.Items))
	for i, vs := range vsList.Items {
		names[i] = vs.Name
	}

	return names, nil
}

func (c *Client) GetVirtualServiceFault(serviceName string) (map[string]interface{}, error) {
	vs, err := c.clientset.NetworkingV1beta1().VirtualServices(c.namespace).Get(
		context.TODO(), serviceName, metav1.GetOptions{},
	)
	if err != nil {
		return nil, err
	}

	result := make(map[string]interface{})
	for i, http := range vs.Spec.Http {
		if http.Fault != nil {
			result[fmt.Sprintf("route_%d", i)] = http.Fault
		}
	}

	return result, nil
}

func (c *Client) GetServiceTopology() (*model.ServiceTopology, error) {
	services, err := c.GetServicesWithDetails()
	if err != nil {
		return nil, err
	}

	vsList, err := c.clientset.NetworkingV1beta1().VirtualServices(c.namespace).List(
		context.TODO(), metav1.ListOptions{},
	)
	if err != nil {
		return nil, fmt.Errorf("failed to list virtual services: %w", err)
	}

	var connections []model.Connection
	serviceSet := make(map[string]bool)
	for _, s := range services {
		serviceSet[s.Name] = true
	}

	for _, vs := range vsList.Items {
		source := vs.Name
		for _, http := range vs.Spec.Http {
			for _, route := range http.Route {
				dest := route.Destination.Host
				if serviceSet[dest] && source != dest {
					connections = append(connections, model.Connection{
						Source:      source,
						Destination: dest,
						Protocol:    "HTTP",
					})
				}
			}
		}
	}

	return &model.ServiceTopology{
		Services:    services,
		Connections: connections,
	}, nil
}

func (c *Client) GetServicesWithDetails() ([]model.ServiceInfo, error) {
	pods, err := c.kubeClientset.CoreV1().Pods(c.namespace).List(
		context.TODO(), metav1.ListOptions{},
	)
	if err != nil {
		return nil, fmt.Errorf("failed to list pods: %w", err)
	}

	services, err := c.kubeClientset.CoreV1().Services(c.namespace).List(
		context.TODO(), metav1.ListOptions{},
	)
	if err != nil {
		return nil, fmt.Errorf("failed to list services: %w", err)
	}

	serviceMap := make(map[string]*model.ServiceInfo)
	for _, svc := range services.Items {
		serviceMap[svc.Name] = &model.ServiceInfo{
			Name:      svc.Name,
			Namespace: svc.Namespace,
			Labels:    svc.Labels,
			Status:    "Running",
			Versions:  []string{},
		}
	}

	versionSet := make(map[string]map[string]bool)
	for _, pod := range pods.Items {
		app := pod.Labels["app"]
		version := pod.Labels["version"]
		if app != "" && version != "" {
			if _, ok := serviceMap[app]; ok {
				if _, ok := versionSet[app]; !ok {
					versionSet[app] = make(map[string]bool)
				}
				versionSet[app][version] = true
			}
		}
	}

	var result []model.ServiceInfo
	for name, info := range serviceMap {
		if versions, ok := versionSet[name]; ok {
			for v := range versions {
				info.Versions = append(info.Versions, v)
			}
		}
		if len(info.Versions) == 0 {
			info.Versions = []string{"v1"}
		}
		result = append(result, *info)
	}

	return result, nil
}

func (c *Client) GetServiceVersions(serviceName string) ([]string, error) {
	pods, err := c.kubeClientset.CoreV1().Pods(c.namespace).List(
		context.TODO(),
		metav1.ListOptions{
			LabelSelector: fmt.Sprintf("app=%s", serviceName),
		},
	)
	if err != nil {
		return nil, fmt.Errorf("failed to list pods: %w", err)
	}

	versionSet := make(map[string]bool)
	for _, pod := range pods.Items {
		if version := pod.Labels["version"]; version != "" {
			versionSet[version] = true
		}
	}

	var versions []string
	for v := range versionSet {
		versions = append(versions, v)
	}
	if len(versions) == 0 {
		versions = []string{"v1"}
	}
	return versions, nil
}

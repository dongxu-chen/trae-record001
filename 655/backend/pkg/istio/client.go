package istio

import (
	"context"
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"sigs.k8s.io/yaml"

	"servicemesh-gateway/pkg/models"
)

var (
	virtualServiceGVR = schema.GroupVersionResource{
		Group:    "networking.istio.io",
		Version:  "v1",
		Resource: "virtualservices",
	}

	destinationRuleGVR = schema.GroupVersionResource{
		Group:    "networking.istio.io",
		Version:  "v1",
		Resource: "destinationrules",
	}
)

type Client struct {
	dynamicClient dynamic.Interface
	config        *rest.Config
}

func NewClient(kubeconfig string) (*Client, error) {
	var config *rest.Config
	var err error

	if kubeconfig != "" {
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
	} else {
		config, err = rest.InClusterConfig()
	}

	if err != nil {
		return nil, fmt.Errorf("failed to create k8s config: %w", err)
	}

	dynamicClient, err := dynamic.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create dynamic client: %w", err)
	}

	return &Client{
		dynamicClient: dynamicClient,
		config:        config,
	}, nil
}

func (c *Client) CreateVirtualService(namespace string, vs *models.VirtualService) error {
	vs.APIVersion = "networking.istio.io/v1"
	vs.Kind = "VirtualService"

	unstructuredObj, err := toUnstructured(vs)
	if err != nil {
		return fmt.Errorf("failed to convert to unstructured: %w", err)
	}

	_, err = c.dynamicClient.Resource(virtualServiceGVR).Namespace(namespace).Create(
		context.Background(),
		unstructuredObj,
		metav1.CreateOptions{},
	)

	return err
}

func (c *Client) UpdateVirtualService(namespace string, vs *models.VirtualService) error {
	vs.APIVersion = "networking.istio.io/v1"
	vs.Kind = "VirtualService"

	unstructuredObj, err := toUnstructured(vs)
	if err != nil {
		return fmt.Errorf("failed to convert to unstructured: %w", err)
	}

	_, err = c.dynamicClient.Resource(virtualServiceGVR).Namespace(namespace).Update(
		context.Background(),
		unstructuredObj,
		metav1.UpdateOptions{},
	)

	return err
}

func (c *Client) GetVirtualService(namespace, name string) (*models.VirtualService, error) {
	obj, err := c.dynamicClient.Resource(virtualServiceGVR).Namespace(namespace).Get(
		context.Background(),
		name,
		metav1.GetOptions{},
	)
	if err != nil {
		return nil, err
	}

	var vs models.VirtualService
	if err := fromUnstructured(obj, &vs); err != nil {
		return nil, err
	}

	return &vs, nil
}

func (c *Client) DeleteVirtualService(namespace, name string) error {
	return c.dynamicClient.Resource(virtualServiceGVR).Namespace(namespace).Delete(
		context.Background(),
		name,
		metav1.DeleteOptions{},
	)
}

func (c *Client) ListVirtualServices(namespace string) ([]*models.VirtualService, error) {
	list, err := c.dynamicClient.Resource(virtualServiceGVR).Namespace(namespace).List(
		context.Background(),
		metav1.ListOptions{},
	)
	if err != nil {
		return nil, err
	}

	var vsList []*models.VirtualService
	for _, item := range list.Items {
		var vs models.VirtualService
		if err := fromUnstructured(&item, &vs); err != nil {
			continue
		}
		vsList = append(vsList, &vs)
	}

	return vsList, nil
}

func (c *Client) CreateDestinationRule(namespace string, dr *models.DestinationRule) error {
	dr.APIVersion = "networking.istio.io/v1"
	dr.Kind = "DestinationRule"

	unstructuredObj, err := toUnstructured(dr)
	if err != nil {
		return fmt.Errorf("failed to convert to unstructured: %w", err)
	}

	_, err = c.dynamicClient.Resource(destinationRuleGVR).Namespace(namespace).Create(
		context.Background(),
		unstructuredObj,
		metav1.CreateOptions{},
	)

	return err
}

func (c *Client) UpdateDestinationRule(namespace string, dr *models.DestinationRule) error {
	dr.APIVersion = "networking.istio.io/v1"
	dr.Kind = "DestinationRule"

	unstructuredObj, err := toUnstructured(dr)
	if err != nil {
		return fmt.Errorf("failed to convert to unstructured: %w", err)
	}

	_, err = c.dynamicClient.Resource(destinationRuleGVR).Namespace(namespace).Update(
		context.Background(),
		unstructuredObj,
		metav1.UpdateOptions{},
	)

	return err
}

func (c *Client) GetDestinationRule(namespace, name string) (*models.DestinationRule, error) {
	obj, err := c.dynamicClient.Resource(destinationRuleGVR).Namespace(namespace).Get(
		context.Background(),
		name,
		metav1.GetOptions{},
	)
	if err != nil {
		return nil, err
	}

	var dr models.DestinationRule
	if err := fromUnstructured(obj, &dr); err != nil {
		return nil, err
	}

	return &dr, nil
}

func (c *Client) DeleteDestinationRule(namespace, name string) error {
	return c.dynamicClient.Resource(destinationRuleGVR).Namespace(namespace).Delete(
		context.Background(),
		name,
		metav1.DeleteOptions{},
	)
}

func (c *Client) ListDestinationRules(namespace string) ([]*models.DestinationRule, error) {
	list, err := c.dynamicClient.Resource(destinationRuleGVR).Namespace(namespace).List(
		context.Background(),
		metav1.ListOptions{},
	)
	if err != nil {
		return nil, err
	}

	var drList []*models.DestinationRule
	for _, item := range list.Items {
		var dr models.DestinationRule
		if err := fromUnstructured(&item, &dr); err != nil {
			continue
		}
		drList = append(drList, &dr)
	}

	return drList, nil
}

func (c *Client) ApplyWeightRouting(rule *models.WeightRouting) error {
	vs := &models.VirtualService{
		Metadata: models.Metadata{
			Name:      rule.ServiceName,
			Namespace: rule.Namespace,
		},
		Spec: models.VSSpec{
			Hosts: []string{rule.ServiceName},
			HTTP: []models.HTTPRoute{
				{
					Route: make([]models.Destination, len(rule.Subsets)),
				},
			},
		},
	}

	for i, subset := range rule.Subsets {
		vs.Spec.HTTP[0].Route[i] = models.Destination{
			Host:   rule.ServiceName,
			Subset: subset.SubsetName,
		}
		vs.Spec.HTTP[0].Route[i] = models.Destination{
			Host:   rule.ServiceName,
			Subset: subset.SubsetName,
		}
	}

	vs.Spec.HTTP[0].Route[0].Host = rule.ServiceName
	vs.Spec.HTTP[0].Route[0].Subset = rule.Subsets[0].SubsetName

	return c.CreateOrUpdateVirtualService(rule.Namespace, vs)
}

func (c *Client) ApplyHeaderRouting(rule *models.HeaderRouting) error {
	vs := &models.VirtualService{
		Metadata: models.Metadata{
			Name:      rule.ServiceName,
			Namespace: rule.Namespace,
		},
		Spec: models.VSSpec{
			Hosts: []string{rule.ServiceName},
			HTTP:  []models.HTTPRoute{},
		},
	}

	matchRoute := models.HTTPRoute{
		Match: []models.HTTPMatch{},
		Route: []models.Destination{
			{
				Host:   rule.ServiceName,
				Subset: rule.TargetSubset,
			},
		},
	}

	for _, match := range rule.MatchRules {
		headers := make(map[string]models.StringMatch)
		switch match.MatchType {
		case "exact":
			headers[match.HeaderName] = models.StringMatch{Exact: match.Value}
		case "prefix":
			headers[match.HeaderName] = models.StringMatch{Prefix: match.Value}
		case "regex":
			headers[match.HeaderName] = models.StringMatch{Regex: match.Value}
		}
		matchRoute.Match = append(matchRoute.Match, models.HTTPMatch{Headers: headers})
	}

	vs.Spec.HTTP = append(vs.Spec.HTTP, matchRoute)

	return c.CreateOrUpdateVirtualService(rule.Namespace, vs)
}

func (c *Client) ApplyTrafficMirror(rule *models.TrafficMirror) error {
	vs, err := c.GetVirtualService(rule.Namespace, rule.SourceService)
	if err != nil {
		vs = &models.VirtualService{
			Metadata: models.Metadata{
				Name:      rule.SourceService,
				Namespace: rule.Namespace,
			},
			Spec: models.VSSpec{
				Hosts: []string{rule.SourceService},
				HTTP: []models.HTTPRoute{
					{
						Route: []models.Destination{
							{
								Host: rule.SourceService,
							},
						},
					},
				},
			},
		}
	}

	mirror := &models.Destination{
		Host: rule.MirrorService,
	}
	if rule.MirrorSubset != "" {
		mirror.Subset = rule.MirrorSubset
	}
	if rule.MirrorPort > 0 {
		mirror.Port = &models.Port{Number: rule.MirrorPort}
	}

	vs.Spec.HTTP[0].Mirror = mirror
	vs.Spec.HTTP[0].MirrorPercentage = &models.Percent{
		Value: float64(rule.Percentage),
	}

	return c.CreateOrUpdateVirtualService(rule.Namespace, vs)
}

func (c *Client) ApplyFaultInjection(rule *models.FaultInjection) error {
	vs, err := c.GetVirtualService(rule.Namespace, rule.ServiceName)
	if err != nil {
		vs = &models.VirtualService{
			Metadata: models.Metadata{
				Name:      rule.ServiceName,
				Namespace: rule.Namespace,
			},
			Spec: models.VSSpec{
				Hosts: []string{rule.ServiceName},
				HTTP: []models.HTTPRoute{
					{
						Route: []models.Destination{
							{
								Host: rule.ServiceName,
							},
						},
					},
				},
			},
		}
	}

	fault := &models.HTTPFaultInjection{}
	switch rule.FaultType {
	case "delay":
		if rule.Delay != nil {
			fault.Delay = &models.DelayFault{
				FixedDelay: rule.Delay.FixedDelay,
				Percentage: float64(rule.Percentage),
			}
		}
	case "abort":
		if rule.Abort != nil {
			fault.Abort = &models.AbortFault{
				HTTPStatus: rule.Abort.HTTPStatus,
				Percentage: float64(rule.Percentage),
			}
		}
	}

	vs.Spec.HTTP[0].Fault = fault

	return c.CreateOrUpdateVirtualService(rule.Namespace, vs)
}

func (c *Client) CreateOrUpdateVirtualService(namespace string, vs *models.VirtualService) error {
	existing, err := c.GetVirtualService(namespace, vs.Metadata.Name)
	if err != nil {
		return c.CreateVirtualService(namespace, vs)
	}
	vs.Metadata.Labels = existing.Metadata.Labels
	return c.UpdateVirtualService(namespace, vs)
}

func toUnstructured(obj interface{}) (*unstructured.Unstructured, error) {
	data, err := yaml.Marshal(obj)
	if err != nil {
		return nil, err
	}

	result := &unstructured.Unstructured{}
	if err := yaml.Unmarshal(data, result); err != nil {
		return nil, err
	}

	return result, nil
}

func fromUnstructured(obj *unstructured.Unstructured, dest interface{}) error {
	data, err := yaml.Marshal(obj.Object)
	if err != nil {
		return err
	}

	return yaml.Unmarshal(data, dest)
}

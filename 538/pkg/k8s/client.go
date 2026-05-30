package k8s

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"k8s-network-policy-recommender/pkg/config"

	v1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

type Client struct {
	clientset *kubernetes.Clientset
}

func NewClient(cfg config.KubernetesConfig) (*Client, error) {
	var config *rest.Config
	var err error

	if cfg.InCluster {
		config, err = rest.InClusterConfig()
	} else {
		kubeconfig := cfg.Kubeconfig
		if kubeconfig == "" {
			home, _ := os.UserHomeDir()
			kubeconfig = filepath.Join(home, ".kube", "config")
		}
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
	}

	if err != nil {
		return nil, err
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	return &Client{clientset: clientset}, nil
}

func (c *Client) GetPods(ctx context.Context, namespace string) ([]PodInfo, error) {
	pods, err := c.clientset.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	var result []PodInfo
	for _, pod := range pods.Items {
		result = append(result, PodInfo{
			Name:      pod.Name,
			Namespace: pod.Namespace,
			Labels:    pod.Labels,
			IP:        pod.Status.PodIP,
		})
	}

	return result, nil
}

func (c *Client) GetNamespaces(ctx context.Context) ([]string, error) {
	ns, err := c.clientset.CoreV1().Namespaces().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	var result []string
	for _, n := range ns.Items {
		result = append(result, n.Name)
	}

	return result, nil
}

func (c *Client) GetNetworkPolicies(ctx context.Context, namespace string) ([]v1.NetworkPolicy, error) {
	nps, err := c.clientset.NetworkingV1().NetworkPolicies(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	return nps.Items, nil
}

func (c *Client) CreateNetworkPolicy(ctx context.Context, namespace string, np *v1.NetworkPolicy) (*v1.NetworkPolicy, error) {
	return c.clientset.NetworkingV1().NetworkPolicies(namespace).Create(ctx, np, metav1.CreateOptions{})
}

type PodInfo struct {
	Name      string            `json:"name"`
	Namespace string            `json:"namespace"`
	Labels    map[string]string `json:"labels"`
	IP        string            `json:"ip"`
}

func (c *Client) ApplyNetworkPolicy(ctx context.Context, namespace string, policy *v1.NetworkPolicy) error {
	existing, err := c.clientset.NetworkingV1().NetworkPolicies(namespace).Get(ctx, policy.Name, metav1.GetOptions{})
	if err != nil {
		_, err := c.clientset.NetworkingV1().NetworkPolicies(namespace).Create(ctx, policy, metav1.CreateOptions{})
		return err
	}

	policy.ResourceVersion = existing.ResourceVersion
	_, err = c.clientset.NetworkingV1().NetworkPolicies(namespace).Update(ctx, policy, metav1.UpdateOptions{})
	return err
}

func (c *Client) DeleteNetworkPolicy(ctx context.Context, namespace, name string) error {
	return c.clientset.NetworkingV1().NetworkPolicies(namespace).Delete(ctx, name, metav1.DeleteOptions{})
}

func (c *Client) GetServices(ctx context.Context, namespace string) ([]ServiceInfo, error) {
	svcs, err := c.clientset.CoreV1().Services(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	var result []ServiceInfo
	for _, svc := range svcs.Items {
		ports := make([]PortInfo, len(svc.Spec.Ports))
		for i, p := range svc.Spec.Ports {
			ports[i] = PortInfo{
				Port:     p.Port,
				Protocol: string(p.Protocol),
				Name:     p.Name,
			}
		}

		result = append(result, ServiceInfo{
			Name:      svc.Name,
			Namespace: svc.Namespace,
			Selector:  svc.Spec.Selector,
			Ports:     ports,
		})
	}

	return result, nil
}

type ServiceInfo struct {
	Name      string            `json:"name"`
	Namespace string            `json:"namespace"`
	Selector  map[string]string `json:"selector"`
	Ports     []PortInfo        `json:"ports"`
}

type PortInfo struct {
	Port     int32  `json:"port"`
	Protocol string `json:"protocol"`
	Name     string `json:"name"`
}

func (c *Client) GetPodSelectorLabels(ctx context.Context, namespace string) (map[string]map[string]string, error) {
	pods, err := c.GetPods(ctx, namespace)
	if err != nil {
		return nil, err
	}

	result := make(map[string]map[string]string)
	for _, pod := range pods {
		key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
		result[key] = pod.Labels
	}

	return result, nil
}

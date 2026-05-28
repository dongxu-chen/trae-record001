package k8sclient

import (
	"context"
	"fmt"
	"path/filepath"

	"k8s-cost-allocation/internal/config"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

type Client struct {
	clientset *kubernetes.Clientset
}

type NamespaceInfo struct {
	Name   string            `json:"name"`
	Labels map[string]string `json:"labels"`
	Phase  string            `json:"phase"`
}

type PodInfo struct {
	Name        string            `json:"name"`
	Namespace   string            `json:"namespace"`
	Labels      map[string]string `json:"labels"`
	CPURequest  float64           `json:"cpuRequest"`
	CPULimit    float64           `json:"cpuLimit"`
	MemoryRequest float64         `json:"memoryRequest"`
	MemoryLimit   float64         `json:"memoryLimit"`
	Status      string            `json:"status"`
}

type PVCInfo struct {
	Name        string  `json:"name"`
	Namespace   string  `json:"namespace"`
	CapacityGB  float64 `json:"capacityGB"`
	StorageClass string `json:"storageClass"`
	Phase       string  `json:"phase"`
}

type NodeInfo struct {
	Name       string            `json:"name"`
	Labels     map[string]string `json:"labels"`
	CPUCapacity float64          `json:"cpuCapacity"`
	MemoryCapacityGB float64     `json:"memoryCapacityGB"`
	Ready      bool              `json:"ready"`
}

func NewClient(cfg config.KubernetesConfig) (*Client, error) {
	var kubeconfig string
	if cfg.Kubeconfig != "" {
		kubeconfig = cfg.Kubeconfig
	} else if !cfg.InCluster {
		if home := homedir.HomeDir(); home != "" {
			kubeconfig = filepath.Join(home, ".kube", "config")
		}
	}

	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create clientset: %w", err)
	}

	return &Client{clientset: clientset}, nil
}

func (c *Client) GetNamespaces(ctx context.Context) ([]NamespaceInfo, error) {
	nsList, err := c.clientset.CoreV1().Namespaces().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	var namespaces []NamespaceInfo
	for _, ns := range nsList.Items {
		namespaces = append(namespaces, NamespaceInfo{
			Name:   ns.Name,
			Labels: ns.Labels,
			Phase:  string(ns.Status.Phase),
		})
	}

	return namespaces, nil
}

func (c *Client) GetPods(ctx context.Context, namespace string) ([]PodInfo, error) {
	podList, err := c.clientset.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	var pods []PodInfo
	for _, pod := range podList.Items {
		var cpuRequest, cpuLimit, memoryRequest, memoryLimit float64
		for _, container := range pod.Spec.Containers {
			cpuRequest += float64(container.Resources.Requests.Cpu().MilliValue()) / 1000
			cpuLimit += float64(container.Resources.Limits.Cpu().MilliValue()) / 1000
			memoryRequest += float64(container.Resources.Requests.Memory().Value()) / (1024 * 1024 * 1024)
			memoryLimit += float64(container.Resources.Limits.Memory().Value()) / (1024 * 1024 * 1024)
		}

		pods = append(pods, PodInfo{
			Name:          pod.Name,
			Namespace:     pod.Namespace,
			Labels:        pod.Labels,
			CPURequest:    cpuRequest,
			CPULimit:      cpuLimit,
			MemoryRequest: memoryRequest,
			MemoryLimit:   memoryLimit,
			Status:        string(pod.Status.Phase),
		})
	}

	return pods, nil
}

func (c *Client) GetAllPods(ctx context.Context) ([]PodInfo, error) {
	return c.GetPods(ctx, "")
}

func (c *Client) GetPVCs(ctx context.Context, namespace string) ([]PVCInfo, error) {
	pvcList, err := c.clientset.CoreV1().PersistentVolumeClaims(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	var pvcs []PVCInfo
	for _, pvc := range pvcList.Items {
		capacity := pvc.Spec.Resources.Requests.Storage()
		capacityGB := float64(capacity.Value()) / (1024 * 1024 * 1024)
		storageClass := ""
		if pvc.Spec.StorageClassName != nil {
			storageClass = *pvc.Spec.StorageClassName
		}

		pvcs = append(pvcs, PVCInfo{
			Name:         pvc.Name,
			Namespace:    pvc.Namespace,
			CapacityGB:   capacityGB,
			StorageClass: storageClass,
			Phase:        string(pvc.Status.Phase),
		})
	}

	return pvcs, nil
}

func (c *Client) GetAllPVCs(ctx context.Context) ([]PVCInfo, error) {
	return c.GetPVCs(ctx, "")
}

func (c *Client) GetNodes(ctx context.Context) ([]NodeInfo, error) {
	nodeList, err := c.clientset.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	var nodes []NodeInfo
	for _, node := range nodeList.Items {
		cpuCapacity := float64(node.Status.Capacity.Cpu().MilliValue()) / 1000
		memoryCapacityGB := float64(node.Status.Capacity.Memory().Value()) / (1024 * 1024 * 1024)

		ready := false
		for _, condition := range node.Status.Conditions {
			if condition.Type == v1.NodeReady && condition.Status == v1.ConditionTrue {
				ready = true
				break
			}
		}

		nodes = append(nodes, NodeInfo{
			Name:             node.Name,
			Labels:           node.Labels,
			CPUCapacity:      cpuCapacity,
			MemoryCapacityGB: memoryCapacityGB,
			Ready:            ready,
		})
	}

	return nodes, nil
}

package k8sclient

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"

	"ci-scheduler/pkg/dag"
)

type K8sClient struct {
	clientset   *kubernetes.Clientset
	namespace   string
	config      *rest.Config
	mu          sync.Mutex
	podLabels   map[string]string
}

type PodStatus struct {
	PodName       string
	TaskID        string
	Status        corev1.PodPhase
	NodeName      string
	CPUUsage      float64
	MemoryUsage   int64
	StartTime     *time.Time
	FinishedTime  *time.Time
	ExitCode      int32
	Reason        string
	Message       string
}

func NewK8sClient(namespace string, kubeconfigPath string) (*K8sClient, error) {
	var config *rest.Config
	var err error

	if kubeconfigPath == "" {
		if home := homedir.HomeDir(); home != "" {
			kubeconfigPath = filepath.Join(home, ".kube", "config")
		}
	}

	if _, err := os.Stat(kubeconfigPath); err == nil {
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfigPath)
		if err != nil {
			return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
		}
	} else {
		config, err = rest.InClusterConfig()
		if err != nil {
			return nil, fmt.Errorf("failed to get in-cluster config: %w", err)
		}
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kubernetes clientset: %w", err)
	}

	if namespace == "" {
		namespace = "default"
	}

	return &K8sClient{
		clientset: clientset,
		namespace: namespace,
		config:    config,
		podLabels: map[string]string{
			"app": "ci-scheduler",
		},
	}, nil
}

func (k *K8sClient) CreatePod(ctx context.Context, task *dag.Task, executorName string) (*corev1.Pod, error) {
	k.mu.Lock()
	defer k.mu.Unlock()

	podName := fmt.Sprintf("ci-%s-%s", task.ID, generateRandomSuffix())

	labels := map[string]string{
		"app":       "ci-scheduler",
		"task-id":   task.ID,
		"executor":  executorName,
		"pipeline":  task.Labels["pipeline"],
	}
	for k, v := range task.Labels {
		labels[k] = v
	}

	resources := corev1.ResourceRequirements{
		Requests: corev1.ResourceList{},
		Limits:   corev1.ResourceList{},
	}

	if task.Resources.CPU > 0 {
		resources.Requests[corev1.ResourceCPU] = resource.MustParse(fmt.Sprintf("%.2f", task.Resources.CPU))
		resources.Limits[corev1.ResourceCPU] = resource.MustParse(fmt.Sprintf("%.2f", task.Resources.CPU*1.2))
	}

	if task.Resources.Memory > 0 {
		resources.Requests[corev1.ResourceMemory] = resource.MustParse(fmt.Sprintf("%dMi", task.Resources.Memory))
		resources.Limits[corev1.ResourceMemory] = resource.MustParse(fmt.Sprintf("%dMi", int64(float64(task.Resources.Memory)*1.2)))
	}

	command := task.Command
	if len(command) == 0 {
		command = []string{"echo", "no command specified"}
	}

	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      podName,
			Namespace: k.namespace,
			Labels:    labels,
			Annotations: map[string]string{
				"task-id":       task.ID,
				"task-name":     task.Name,
				"executor-name": executorName,
			},
		},
		Spec: corev1.PodSpec{
			RestartPolicy: corev1.RestartPolicyNever,
			Containers: []corev1.Container{
				{
					Name:      "ci-task",
					Image:     task.Image,
					Command:   command,
					Resources: resources,
				},
			},
		},
	}

	createdPod, err := k.clientset.CoreV1().Pods(k.namespace).Create(ctx, pod, metav1.CreateOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to create pod: %w", err)
	}

	return createdPod, nil
}

func (k *K8sClient) DeletePod(ctx context.Context, podName string) error {
	k.mu.Lock()
	defer k.mu.Unlock()

	deletePolicy := metav1.DeletePropagationForeground
	err := k.clientset.CoreV1().Pods(k.namespace).Delete(ctx, podName, metav1.DeleteOptions{
		PropagationPolicy: &deletePolicy,
	})
	if err != nil && !errors.IsNotFound(err) {
		return fmt.Errorf("failed to delete pod %s: %w", podName, err)
	}
	return nil
}

func (k *K8sClient) GetPodStatus(ctx context.Context, podName string) (*PodStatus, error) {
	k.mu.Lock()
	defer k.mu.Unlock()

	pod, err := k.clientset.CoreV1().Pods(k.namespace).Get(ctx, podName, metav1.GetOptions{})
	if err != nil {
		if errors.IsNotFound(err) {
			return nil, fmt.Errorf("pod %s not found", podName)
		}
		return nil, fmt.Errorf("failed to get pod %s: %w", podName, err)
	}

	status := &PodStatus{
		PodName:    pod.Name,
		TaskID:     pod.Labels["task-id"],
		Status:     pod.Status.Phase,
		NodeName:   pod.Spec.NodeName,
		StartTime:  pod.Status.StartTime.Time,
	}

	for _, containerStatus := range pod.Status.ContainerStatuses {
		if containerStatus.Name == "ci-task" {
			if containerStatus.State.Terminated != nil {
				status.FinishedTime = &containerStatus.State.Terminated.FinishedAt.Time
				status.ExitCode = containerStatus.State.Terminated.ExitCode
				status.Reason = containerStatus.State.Terminated.Reason
				status.Message = containerStatus.State.Terminated.Message
			}
		}
	}

	return status, nil
}

func (k *K8sClient) ListPods(ctx context.Context, selector map[string]string) ([]corev1.Pod, error) {
	k.mu.Lock()
	defer k.mu.Unlock()

	labelSelector := labels.SelectorFromSet(selector)
	pods, err := k.clientset.CoreV1().Pods(k.namespace).List(ctx, metav1.ListOptions{
		LabelSelector: labelSelector.String(),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to list pods: %w", err)
	}

	return pods.Items, nil
}

func (k *K8sClient) GetPodLogs(ctx context.Context, podName string) (string, error) {
	k.mu.Lock()
	defer k.mu.Unlock()

	tailLines := int64(1000)
	logs, err := k.clientset.CoreV1().Pods(k.namespace).GetLogs(podName, &corev1.PodLogOptions{
		Container: "ci-task",
		TailLines: &tailLines,
	}).DoRaw(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to get logs for pod %s: %w", podName, err)
	}

	return string(logs), nil
}

func (k *K8sClient) WatchPods(ctx context.Context, labelSelector map[string]string, callback func(*corev1.Pod)) error {
	selector := labels.SelectorFromSet(labelSelector)
	watcher, err := k.clientset.CoreV1().Pods(k.namespace).Watch(ctx, metav1.ListOptions{
		LabelSelector: selector.String(),
		Watch:         true,
	})
	if err != nil {
		return fmt.Errorf("failed to watch pods: %w", err)
	}
	defer watcher.Stop()

	for event := range watcher.ResultChan() {
		pod, ok := event.Object.(*corev1.Pod)
		if ok {
			callback(pod)
		}
	}

	return nil
}

func (k *K8sClient) GetNodeResources(ctx context.Context, nodeName string) (cpu float64, memory int64, err error) {
	k.mu.Lock()
	defer k.mu.Unlock()

	node, err := k.clientset.CoreV1().Nodes().Get(ctx, nodeName, metav1.GetOptions{})
	if err != nil {
		return 0, 0, fmt.Errorf("failed to get node %s: %w", nodeName, err)
	}

	cpuQuantity := node.Status.Allocatable[corev1.ResourceCPU]
	memoryQuantity := node.Status.Allocatable[corev1.ResourceMemory]

	cpu = float64(cpuQuantity.MilliValue()) / 1000.0
	memory = memoryQuantity.Value() / (1024 * 1024)

	return cpu, memory, nil
}

func (k *K8sClient) ListNodes(ctx context.Context) ([]string, error) {
	k.mu.Lock()
	defer k.mu.Unlock()

	nodes, err := k.clientset.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list nodes: %w", err)
	}

	nodeNames := make([]string, 0, len(nodes.Items))
	for _, node := range nodes.Items {
		nodeNames = append(nodeNames, node.Name)
	}

	return nodeNames, nil
}

func (k *K8sClient) CleanupCompletedPods(ctx context.Context, olderThan time.Duration) error {
	k.mu.Lock()
	defer k.mu.Unlock()

	pods, err := k.ListPods(ctx, k.podLabels)
	if err != nil {
		return err
	}

	cutoff := time.Now().Add(-olderThan)

	for _, pod := range pods {
		if pod.Status.Phase == corev1.PodSucceeded || pod.Status.Phase == corev1.PodFailed {
			if pod.Status.StartTime != nil && pod.Status.StartTime.Time.Before(cutoff) {
				err := k.DeletePod(ctx, pod.Name)
				if err != nil {
					fmt.Printf("Warning: failed to delete pod %s: %v\n", pod.Name, err)
				}
			}
		}
	}

	return nil
}

func generateRandomSuffix() string {
	return fmt.Sprintf("%d", time.Now().UnixNano()%1000000)
}

func IsPodCompleted(status corev1.PodPhase) bool {
	return status == corev1.PodSucceeded || status == corev1.PodFailed
}

func IsPodSuccessful(status corev1.PodPhase) bool {
	return status == corev1.PodSucceeded
}

package kubernetes

import (
	"context"
	"fmt"
	"path/filepath"
	"sync"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	autoscalingv1 "k8s.io/api/autoscaling/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"

	"github.com/sirupsen/logrus"
)

type Client struct {
	clientset *kubernetes.Clientset
	config    *rest.Config
	logger    *logrus.Logger
	mu        sync.RWMutex
}

type DeploymentInfo struct {
	Name              string
	Namespace         string
	Replicas          int32
	ReadyReplicas     int32
	AvailableReplicas int32
	UpdatedReplicas   int32
	CreationTime      time.Time
	Labels            map[string]string
}

type ClientConfig struct {
	KubeConfigPath string
	InCluster      bool
}

func NewClient(config ClientConfig, logger *logrus.Logger) (*Client, error) {
	var (
		cfg *rest.Config
		err error
	)

	if config.InCluster {
		cfg, err = rest.InClusterConfig()
		if err != nil {
			return nil, fmt.Errorf("failed to get in-cluster config: %w", err)
		}
	} else {
		kubeconfig := config.KubeConfigPath
		if kubeconfig == "" {
			if home := homedir.HomeDir(); home != "" {
				kubeconfig = filepath.Join(home, ".kube", "config")
			}
		}

		cfg, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
		}
	}

	clientset, err := kubernetes.NewForConfig(cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create kubernetes client: %w", err)
	}

	return &Client{
		clientset: clientset,
		config:    cfg,
		logger:    logger,
	}, nil
}

func (c *Client) GetDeployment(ctx context.Context, name, namespace string) (*DeploymentInfo, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	deployment, err := c.clientset.AppsV1().Deployments(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get deployment %s/%s: %w", namespace, name, err)
	}

	return &DeploymentInfo{
		Name:              deployment.Name,
		Namespace:         deployment.Namespace,
		Replicas:          *deployment.Spec.Replicas,
		ReadyReplicas:     deployment.Status.ReadyReplicas,
		AvailableReplicas: deployment.Status.AvailableReplicas,
		UpdatedReplicas:   deployment.Status.UpdatedReplicas,
		CreationTime:      deployment.CreationTimestamp.Time,
		Labels:            deployment.Labels,
	}, nil
}

func (c *Client) GetReplicas(ctx context.Context, name, namespace string) (int32, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	deployment, err := c.clientset.AppsV1().Deployments(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return 0, err
	}

	return *deployment.Spec.Replicas, nil
}

func (c *Client) ScaleDeployment(ctx context.Context, name, namespace string, replicas int32) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if replicas < 0 {
		return fmt.Errorf("replicas cannot be negative: %d", replicas)
	}

	scale := &autoscalingv1.Scale{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
		},
		Spec: autoscalingv1.ScaleSpec{
			Replicas: replicas,
		},
	}

	_, err := c.clientset.AppsV1().Deployments(namespace).UpdateScale(ctx, name, scale, metav1.UpdateOptions{})
	if err != nil {
		return fmt.Errorf("failed to scale deployment %s/%s to %d replicas: %w", namespace, name, replicas, err)
	}

	c.logger.Infof("Successfully scaled deployment %s/%s to %d replicas", namespace, name, replicas)
	return nil
}

func (c *Client) ScaleUp(ctx context.Context, name, namespace string, increment int32) (int32, error) {
	currentReplicas, err := c.GetReplicas(ctx, name, namespace)
	if err != nil {
		return 0, err
	}

	newReplicas := currentReplicas + increment
	if err := c.ScaleDeployment(ctx, name, namespace, newReplicas); err != nil {
		return 0, err
	}

	return newReplicas, nil
}

func (c *Client) ScaleDown(ctx context.Context, name, namespace string, decrement int32) (int32, error) {
	currentReplicas, err := c.GetReplicas(ctx, name, namespace)
	if err != nil {
		return 0, err
	}

	newReplicas := currentReplicas - decrement
	if newReplicas < 0 {
		newReplicas = 0
	}

	if err := c.ScaleDeployment(ctx, name, namespace, newReplicas); err != nil {
		return 0, err
	}

	return newReplicas, nil
}

func (c *Client) PatchDeploymentReplicas(ctx context.Context, name, namespace string, replicas int32) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	patch := fmt.Sprintf(`{"spec":{"replicas":%d}}`, replicas)
	_, err := c.clientset.AppsV1().Deployments(namespace).Patch(
		ctx,
		name,
		types.StrategicMergePatchType,
		[]byte(patch),
		metav1.PatchOptions{},
	)

	if err != nil {
		return fmt.Errorf("failed to patch deployment %s/%s: %w", namespace, name, err)
	}

	return nil
}

func (c *Client) WaitForDeploymentReady(ctx context.Context, name, namespace string, timeout time.Duration) error {
	c.mu.RLock()
	defer c.mu.RUnlock()

	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		deployment, err := c.clientset.AppsV1().Deployments(namespace).Get(ctx, name, metav1.GetOptions{})
		if err != nil {
			return err
		}

		specReplicas := *deployment.Spec.Replicas
		readyReplicas := deployment.Status.ReadyReplicas
		availableReplicas := deployment.Status.AvailableReplicas

		if readyReplicas == specReplicas && availableReplicas == specReplicas {
			c.logger.Infof("Deployment %s/%s is ready with %d replicas", namespace, name, specReplicas)
			return nil
		}

		c.logger.Infof("Waiting for deployment %s/%s: spec=%d, ready=%d, available=%d",
			namespace, name, specReplicas, readyReplicas, availableReplicas)

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(5 * time.Second):
		}
	}

	return fmt.Errorf("timeout waiting for deployment %s/%s to be ready", namespace, name)
}

func (c *Client) ListDeployments(ctx context.Context, namespace string, labelSelector string) ([]*DeploymentInfo, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	opts := metav1.ListOptions{}
	if labelSelector != "" {
		opts.LabelSelector = labelSelector
	}

	deployments, err := c.clientset.AppsV1().Deployments(namespace).List(ctx, opts)
	if err != nil {
		return nil, fmt.Errorf("failed to list deployments: %w", err)
	}

	var result []*DeploymentInfo
	for _, deployment := range deployments.Items {
		result = append(result, &DeploymentInfo{
			Name:              deployment.Name,
			Namespace:         deployment.Namespace,
			Replicas:          *deployment.Spec.Replicas,
			ReadyReplicas:     deployment.Status.ReadyReplicas,
			AvailableReplicas: deployment.Status.AvailableReplicas,
			UpdatedReplicas:   deployment.Status.UpdatedReplicas,
			CreationTime:      deployment.CreationTimestamp.Time,
			Labels:            deployment.Labels,
		})
	}

	return result, nil
}

func (c *Client) GetDeploymentEvents(ctx context.Context, name, namespace string) ([]string, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	fieldSelector := fmt.Sprintf("involvedObject.name=%s,involvedObject.kind=Deployment", name)
	events, err := c.clientset.CoreV1().Events(namespace).List(ctx, metav1.ListOptions{
		FieldSelector: fieldSelector,
	})
	if err != nil {
		return nil, err
	}

	var messages []string
	for _, event := range events.Items {
		messages = append(messages, fmt.Sprintf("[%s] %s: %s", event.Type, event.Reason, event.Message))
	}

	return messages, nil
}

func (c *Client) RestartDeployment(ctx context.Context, name, namespace string) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	data := fmt.Sprintf(`{"spec":{"template":{"metadata":{"annotations":{"kubectl.kubernetes.io/restartedAt":"%s"}}}}}`,
		time.Now().Format(time.RFC3339))

	_, err := c.clientset.AppsV1().Deployments(namespace).Patch(
		ctx,
		name,
		types.StrategicMergePatchType,
		[]byte(data),
		metav1.PatchOptions{},
	)

	if err != nil {
		return fmt.Errorf("failed to restart deployment %s/%s: %w", namespace, name, err)
	}

	c.logger.Infof("Successfully restarted deployment %s/%s", namespace, name)
	return nil
}

func (c *Client) GetStatefulSetReplicas(ctx context.Context, name, namespace string) (int32, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	statefulSet, err := c.clientset.AppsV1().StatefulSets(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return 0, err
	}

	return *statefulSet.Spec.Replicas, nil
}

func (c *Client) ScaleStatefulSet(ctx context.Context, name, namespace string, replicas int32) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if replicas < 0 {
		return fmt.Errorf("replicas cannot be negative: %d", replicas)
	}

	scale := &autoscalingv1.Scale{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
		},
		Spec: autoscalingv1.ScaleSpec{
			Replicas: replicas,
		},
	}

	_, err := c.clientset.AppsV1().StatefulSets(namespace).UpdateScale(ctx, name, scale, metav1.UpdateOptions{})
	if err != nil {
		return fmt.Errorf("failed to scale statefulset %s/%s to %d replicas: %w", namespace, name, replicas, err)
	}

	c.logger.Infof("Successfully scaled statefulset %s/%s to %d replicas", namespace, name, replicas)
	return nil
}

func (c *Client) HealthCheck(ctx context.Context) error {
	c.mu.RLock()
	defer c.mu.RUnlock()

	_, err := c.clientset.Discovery().ServerVersion()
	return err
}

func (c *Client) Close() error {
	return nil
}

type ScalableResource interface {
	GetReplicas(ctx context.Context, name, namespace string) (int32, error)
	Scale(ctx context.Context, name, namespace string, replicas int32) error
	WaitForReady(ctx context.Context, name, namespace string, timeout time.Duration) error
}

type DeploymentScaler struct {
	client *Client
}

func (d *DeploymentScaler) GetReplicas(ctx context.Context, name, namespace string) (int32, error) {
	return d.client.GetReplicas(ctx, name, namespace)
}

func (d *DeploymentScaler) Scale(ctx context.Context, name, namespace string, replicas int32) error {
	return d.client.ScaleDeployment(ctx, name, namespace, replicas)
}

func (d *DeploymentScaler) WaitForReady(ctx context.Context, name, namespace string, timeout time.Duration) error {
	return d.client.WaitForDeploymentReady(ctx, name, namespace, timeout)
}

type StatefulSetScaler struct {
	client *Client
}

func (s *StatefulSetScaler) GetReplicas(ctx context.Context, name, namespace string) (int32, error) {
	return s.client.GetStatefulSetReplicas(ctx, name, namespace)
}

func (s *StatefulSetScaler) Scale(ctx context.Context, name, namespace string, replicas int32) error {
	return s.client.ScaleStatefulSet(ctx, name, namespace, replicas)
}

func (s *StatefulSetScaler) WaitForReady(ctx context.Context, name, namespace string, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		statefulSet, err := s.client.clientset.AppsV1().StatefulSets(namespace).Get(ctx, name, metav1.GetOptions{})
		if err != nil {
			return err
		}

		specReplicas := *statefulSet.Spec.Replicas
		readyReplicas := statefulSet.Status.ReadyReplicas

		if readyReplicas == specReplicas {
			return nil
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(5 * time.Second):
		}
	}

	return fmt.Errorf("timeout waiting for statefulset %s/%s to be ready", namespace, name)
}

func (c *Client) GetScaler(resourceType string) (ScalableResource, error) {
	switch resourceType {
	case "deployment", "deployments":
		return &DeploymentScaler{client: c}, nil
	case "statefulset", "statefulsets":
		return &StatefulSetScaler{client: c}, nil
	default:
		return nil, fmt.Errorf("unsupported resource type: %s", resourceType)
	}
}

package istio

import (
	"context"
	"fmt"

	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	istioclient "istio.io/client-go/pkg/clientset/versioned"
	securityv1 "istio.io/client-go/pkg/apis/security/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	"mesh-security-platform/internal/config"
	"mesh-security-platform/internal/models"
)

type Client struct {
	clientset *istioclient.Clientset
	namespace string
}

func NewClient(cfg *config.Config) (*Client, error) {
	var kubeConfig *rest.Config
	var err error

	if cfg.Kubernetes.InCluster {
		kubeConfig, err = rest.InClusterConfig()
	} else {
		kubeConfig, err = clientcmd.BuildConfigFromFlags("", cfg.Kubernetes.KubeConfig)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to build kube config: %w", err)
	}

	clientset, err := istioclient.NewForConfig(kubeConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create istio client: %w", err)
	}

	return &Client{
		clientset: clientset,
		namespace: cfg.Istio.Namespace,
	}, nil
}

func (c *Client) ListPeerAuthentications(ctx context.Context, namespace string) ([]securityv1.PeerAuthentication, error) {
	if namespace == "" {
		namespace = c.namespace
	}

	list, err := c.clientset.SecurityV1().PeerAuthentications(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list peer authentications: %w", err)
	}

	return list.Items, nil
}

func (c *Client) GetPeerAuthentication(ctx context.Context, namespace, name string) (*securityv1.PeerAuthentication, error) {
	return c.clientset.SecurityV1().PeerAuthentications(namespace).Get(ctx, name, metav1.GetOptions{})
}

func (c *Client) CreatePeerAuthentication(ctx context.Context, namespace string, pa *securityv1.PeerAuthentication) (*securityv1.PeerAuthentication, error) {
	return c.clientset.SecurityV1().PeerAuthentications(namespace).Create(ctx, pa, metav1.CreateOptions{})
}

func (c *Client) UpdatePeerAuthentication(ctx context.Context, namespace string, pa *securityv1.PeerAuthentication) (*securityv1.PeerAuthentication, error) {
	return c.clientset.SecurityV1().PeerAuthentications(namespace).Update(ctx, pa, metav1.UpdateOptions{})
}

func (c *Client) DeletePeerAuthentication(ctx context.Context, namespace, name string) error {
	return c.clientset.SecurityV1().PeerAuthentications(namespace).Delete(ctx, name, metav1.DeleteOptions{})
}

func (c *Client) ListAuthorizationPolicies(ctx context.Context, namespace string) ([]securityv1.AuthorizationPolicy, error) {
	list, err := c.clientset.SecurityV1().AuthorizationPolicies(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list authorization policies: %w", err)
	}

	return list.Items, nil
}

func (c *Client) GetAuthorizationPolicy(ctx context.Context, namespace, name string) (*securityv1.AuthorizationPolicy, error) {
	return c.clientset.SecurityV1().AuthorizationPolicies(namespace).Get(ctx, name, metav1.GetOptions{})
}

func (c *Client) CreateAuthorizationPolicy(ctx context.Context, namespace string, ap *securityv1.AuthorizationPolicy) (*securityv1.AuthorizationPolicy, error) {
	return c.clientset.SecurityV1().AuthorizationPolicies(namespace).Create(ctx, ap, metav1.CreateOptions{})
}

func (c *Client) UpdateAuthorizationPolicy(ctx context.Context, namespace string, ap *securityv1.AuthorizationPolicy) (*securityv1.AuthorizationPolicy, error) {
	return c.clientset.SecurityV1().AuthorizationPolicies(namespace).Update(ctx, ap, metav1.UpdateOptions{})
}

func (c *Client) DeleteAuthorizationPolicy(ctx context.Context, namespace, name string) error {
	return c.clientset.SecurityV1().AuthorizationPolicies(namespace).Delete(ctx, name, metav1.DeleteOptions{})
}

func (c *Client) ListRequestAuthentications(ctx context.Context, namespace string) ([]securityv1.RequestAuthentication, error) {
	list, err := c.clientset.SecurityV1().RequestAuthentications(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list request authentications: %w", err)
	}

	return list.Items, nil
}

func (c *Client) GetRequestAuthentication(ctx context.Context, namespace, name string) (*securityv1.RequestAuthentication, error) {
	return c.clientset.SecurityV1().RequestAuthentications(namespace).Get(ctx, name, metav1.GetOptions{})
}

func (c *Client) CreateRequestAuthentication(ctx context.Context, namespace string, ra *securityv1.RequestAuthentication) (*securityv1.RequestAuthentication, error) {
	return c.clientset.SecurityV1().RequestAuthentications(namespace).Create(ctx, ra, metav1.CreateOptions{})
}

func (c *Client) UpdateRequestAuthentication(ctx context.Context, namespace string, ra *securityv1.RequestAuthentication) (*securityv1.RequestAuthentication, error) {
	return c.clientset.SecurityV1().RequestAuthentications(namespace).Update(ctx, ra, metav1.UpdateOptions{})
}

func (c *Client) DeleteRequestAuthentication(ctx context.Context, namespace, name string) error {
	return c.clientset.SecurityV1().RequestAuthentications(namespace).Delete(ctx, name, metav1.DeleteOptions{})
}

func ConvertToPolicy(pa *securityv1.PeerAuthentication) *models.Policy {
	return &models.Policy{
		ID:        string(pa.UID),
		Name:      pa.Name,
		Type:      models.PolicyTypeMTLS,
		Namespace: pa.Namespace,
		Status:    models.PolicyStatusActive,
		CreatedAt: pa.CreationTimestamp.Time,
		Spec: map[string]interface{}{
			"mtls": pa.Spec,
		},
	}
}

func ConvertAuthPolicyToPolicy(ap *securityv1.AuthorizationPolicy) *models.Policy {
	return &models.Policy{
		ID:        string(ap.UID),
		Name:      ap.Name,
		Type:      models.PolicyTypeAuthorization,
		Namespace: ap.Namespace,
		Status:    models.PolicyStatusActive,
		CreatedAt: ap.CreationTimestamp.Time,
		Spec: map[string]interface{}{
			"action": ap.Spec.Action,
			"rules":  ap.Spec.Rules,
		},
	}
}

func ConvertRequestAuthToPolicy(ra *securityv1.RequestAuthentication) *models.Policy {
	return &models.Policy{
		ID:        string(ra.UID),
		Name:      ra.Name,
		Type:      models.PolicyTypeRequestAuth,
		Namespace: ra.Namespace,
		Status:    models.PolicyStatusActive,
		CreatedAt: ra.CreationTimestamp.Time,
		Spec: map[string]interface{}{
			"jwt_rules": ra.Spec.JwtRules,
		},
	}
}

package scanner

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"

	"k8s-auditor/pkg/audit"
)

type Scanner struct {
	clientset     *kubernetes.Clientset
	dynamicClient dynamic.Interface
	namespace     string
}

type DockerConfig struct {
	Auths map[string]DockerAuth `json:"auths"`
}

type DockerAuth struct {
	Auth string `json:"auth"`
}

func New(kubeconfig, namespace string) (*Scanner, error) {
	if kubeconfig == "" {
		if home := homedir.HomeDir(); home != "" {
			kubeconfig = filepath.Join(home, ".kube", "config")
		}
	}

	if _, err := os.Stat(kubeconfig); os.IsNotExist(err) {
		kubeconfig = ""
	}

	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		return nil, fmt.Errorf("failed to build config: %w", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create clientset: %w", err)
	}

	dynamicClient, err := dynamic.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create dynamic client: %w", err)
	}

	return &Scanner{
		clientset:     clientset,
		dynamicClient: dynamicClient,
		namespace:     namespace,
	}, nil
}

func (s *Scanner) ScanAll(ctx context.Context, resourceTypes []string) ([]audit.ResourceInfo, error) {
	var allResources []audit.ResourceInfo

	resourceMap := map[string]schema.GroupVersionResource{
		"pods":                   {Group: "", Version: "v1", Resource: "pods"},
		"services":               {Group: "", Version: "v1", Resource: "services"},
		"configmaps":             {Group: "", Version: "v1", Resource: "configmaps"},
		"secrets":                {Group: "", Version: "v1", Resource: "secrets"},
		"deployments":            {Group: "apps", Version: "v1", Resource: "deployments"},
		"statefulsets":           {Group: "apps", Version: "v1", Resource: "statefulsets"},
		"daemonsets":             {Group: "apps", Version: "v1", Resource: "daemonsets"},
		"ingresses":              {Group: "networking.k8s.io", Version: "v1", Resource: "ingresses"},
		"persistentvolumeclaims": {Group: "", Version: "v1", Resource: "persistentvolumeclaims"},
	}

	for _, rt := range resourceTypes {
		gvr, ok := resourceMap[rt]
		if !ok {
			continue
		}

		resources, err := s.scanResource(ctx, gvr, rt)
		if err != nil {
			return nil, fmt.Errorf("failed to scan %s: %w", rt, err)
		}
		allResources = append(allResources, resources...)
	}

	return allResources, nil
}

func (s *Scanner) scanResource(ctx context.Context, gvr schema.GroupVersionResource, resourceType string) ([]audit.ResourceInfo, error) {
	var resources []audit.ResourceInfo

	list, err := s.dynamicClient.Resource(gvr).Namespace(s.namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	for _, item := range list.Items {
		info := audit.ResourceInfo{
			Type:      resourceType,
			Namespace: item.GetNamespace(),
			Name:      item.GetName(),
			Labels:    item.GetLabels(),
			Spec:      item.Object,
		}
		resources = append(resources, info)
	}

	return resources, nil
}

func (s *Scanner) GetNamespaces(ctx context.Context) ([]corev1.Namespace, error) {
	nsList, err := s.clientset.CoreV1().Namespaces().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}
	return nsList.Items, nil
}

func (s *Scanner) GetResourceQuotas(ctx context.Context, namespace string) ([]corev1.ResourceQuota, error) {
	rqList, err := s.clientset.CoreV1().ResourceQuotas(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}
	return rqList.Items, nil
}

func (s *Scanner) GetPodsInNamespace(ctx context.Context, namespace string) ([]corev1.Pod, error) {
	podList, err := s.clientset.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}
	return podList.Items, nil
}

func (s *Scanner) GetImagePullSecrets(ctx context.Context, namespace string) (map[string]bool, error) {
	registries := make(map[string]bool)

	secretList, err := s.clientset.CoreV1().Secrets(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	for _, secret := range secretList.Items {
		if secret.Type != corev1.SecretTypeDockerConfigJson {
			continue
		}

		dockerConfigBytes, ok := secret.Data[corev1.DockerConfigJsonKey]
		if !ok {
			continue
		}

		var dockerConfig DockerConfig
		if err := json.Unmarshal(dockerConfigBytes, &dockerConfig); err != nil {
			continue
		}

		for registry := range dockerConfig.Auths {
			registries[registry] = true
		}
	}

	return registries, nil
}

func (s *Scanner) GetServiceAccountImagePullSecrets(ctx context.Context, namespace string) (map[string]bool, error) {
	registries := make(map[string]bool)

	saList, err := s.clientset.CoreV1().ServiceAccounts(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}

	for _, sa := range saList.Items {
		for _, imgPullSecret := range sa.ImagePullSecrets {
			secret, err := s.clientset.CoreV1().Secrets(namespace).Get(ctx, imgPullSecret.Name, metav1.GetOptions{})
			if err != nil {
				continue
			}

			if secret.Type != corev1.SecretTypeDockerConfigJson {
				continue
			}

			dockerConfigBytes, ok := secret.Data[corev1.DockerConfigJsonKey]
			if !ok {
				continue
			}

			var dockerConfig DockerConfig
			if err := json.Unmarshal(dockerConfigBytes, &dockerConfig); err != nil {
				continue
			}

			for registry := range dockerConfig.Auths {
				registries[registry] = true
			}
		}
	}

	return registries, nil
}

func (s *Scanner) GetClientset() *kubernetes.Clientset {
	return s.clientset
}

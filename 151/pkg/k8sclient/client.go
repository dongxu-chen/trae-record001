package k8sclient

import (
	"path/filepath"

	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
	istio "istio.io/client-go/pkg/clientset/versioned"
)

type Client struct {
	KubeClient   *kubernetes.Clientset
	IstioClient  *istio.Clientset
	RestConfig   *rest.Config
}

func NewClient(kubeConfigPath string) (*Client, error) {
	config, err := getKubeConfig(kubeConfigPath)
	if err != nil {
		return nil, err
	}

	kubeClient, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	istioClient, err := istio.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	return &Client{
		KubeClient:  kubeClient,
		IstioClient: istioClient,
		RestConfig:  config,
	}, nil
}

func getKubeConfig(kubeConfigPath string) (*rest.Config, error) {
	if kubeConfigPath == "" {
		if home := homedir.HomeDir(); home != "" {
			kubeConfigPath = filepath.Join(home, ".kube", "config")
		}
	}

	config, err := clientcmd.BuildConfigFromFlags("", kubeConfigPath)
	if err != nil {
		config, err = rest.InClusterConfig()
		if err != nil {
			return nil, err
		}
	}

	return config, nil
}

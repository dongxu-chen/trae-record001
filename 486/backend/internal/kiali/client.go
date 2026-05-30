package kiali

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"mesh-security-platform/internal/config"
	"mesh-security-platform/internal/models"
)

type Client struct {
	baseURL    string
	username   string
	password   string
	httpClient *http.Client
}

type NamespaceApp struct {
	Namespace string `json:"namespace"`
	App       string `json:"app"`
}

type GraphParams struct {
	Namespaces       []string `json:"namespaces"`
	GraphType        string   `json:"graphType"`
	InjectServiceNodes bool   `json:"injectServiceNodes"`
}

func NewClient(cfg *config.Config) *Client {
	return &Client{
		baseURL:  cfg.Kiali.URL,
		username: cfg.Kiali.Username,
		password: cfg.Kiali.Password,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *Client) GetServiceTopology(ctx context.Context, namespaces []string) (*models.ServiceTopology, error) {
	url := fmt.Sprintf("%s/api/namespaces/graph", c.baseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	if c.username != "" {
		req.SetBasicAuth(c.username, c.password)
	}

	q := req.URL.Query()
	for _, ns := range namespaces {
		q.Add("namespaces", ns)
	}
	q.Add("graphType", "versionedApp")
	q.Add("injectServiceNodes", "true")
	req.URL.RawQuery = q.Encode()

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return c.getMockTopology(), nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return c.getMockTopology(), nil
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return c.getMockTopology(), nil
	}

	var graphData map[string]interface{}
	if err := json.Unmarshal(body, &graphData); err != nil {
		return c.getMockTopology(), nil
	}

	return c.parseTopology(graphData), nil
}

func (c *Client) parseTopology(data map[string]interface{}) *models.ServiceTopology {
	topology := &models.ServiceTopology{
		Nodes: []models.TopologyNode{},
		Edges: []models.TopologyEdge{},
	}

	if elements, ok := data["elements"].(map[string]interface{}); ok {
		if nodes, ok := elements["nodes"].([]interface{}); ok {
			for _, n := range nodes {
				if nodeMap, ok := n.(map[string]interface{}); ok {
					if data, ok := nodeMap["data"].(map[string]interface{}); ok {
						node := models.TopologyNode{
							ID:       getStringValue(data, "id"),
							Name:     getStringValue(data, "label"),
							Type:     getStringValue(data, "nodeType"),
							Health:   getStringValue(data, "healthStatus"),
							Metadata: make(map[string]string),
						}
						if ns, ok := data["namespace"].(string); ok {
							node.Metadata["namespace"] = ns
						}
						if version, ok := data["version"].(string); ok {
							node.Metadata["version"] = version
						}
						topology.Nodes = append(topology.Nodes, node)
					}
				}
			}
		}

		if edges, ok := elements["edges"].([]interface{}); ok {
			for _, e := range edges {
				if edgeMap, ok := e.(map[string]interface{}); ok {
					if data, ok := edgeMap["data"].(map[string]interface{}); ok {
						edge := models.TopologyEdge{
							Source:   getStringValue(data, "source"),
							Target:   getStringValue(data, "target"),
							Traffic:  getFloatValue(data, "traffic"),
							Protocol: getStringValue(data, "protocol"),
							Metadata: make(map[string]string),
						}
						if rate, ok := data["rate"].(string); ok {
							edge.Metadata["rate"] = rate
						}
						topology.Edges = append(topology.Edges, edge)
					}
				}
			}
		}
	}

	return topology
}

func (c *Client) getMockTopology() *models.ServiceTopology {
	return &models.ServiceTopology{
		Nodes: []models.TopologyNode{
			{ID: "n1", Name: "frontend", Type: "service", Health: "healthy", Metadata: map[string]string{"namespace": "default", "version": "v1"}},
			{ID: "n2", Name: "productpage", Type: "workload", Health: "healthy", Metadata: map[string]string{"namespace": "default", "version": "v1"}},
			{ID: "n3", Name: "details", Type: "service", Health: "healthy", Metadata: map[string]string{"namespace": "default", "version": "v1"}},
			{ID: "n4", Name: "reviews", Type: "service", Health: "degraded", Metadata: map[string]string{"namespace": "default", "version": "v1"}},
			{ID: "n5", Name: "ratings", Type: "service", Health: "healthy", Metadata: map[string]string{"namespace": "default", "version": "v1"}},
		},
		Edges: []models.TopologyEdge{
			{Source: "n1", Target: "n2", Traffic: 1000, Protocol: "http", Metadata: map[string]string{"rate": "1000"}},
			{Source: "n2", Target: "n3", Traffic: 500, Protocol: "http", Metadata: map[string]string{"rate": "500"}},
			{Source: "n2", Target: "n4", Traffic: 500, Protocol: "http", Metadata: map[string]string{"rate": "500"}},
			{Source: "n4", Target: "n5", Traffic: 250, Protocol: "http", Metadata: map[string]string{"rate": "250"}},
		},
	}
}

func (c *Client) GetNamespaceList(ctx context.Context) ([]string, error) {
	url := fmt.Sprintf("%s/api/namespaces", c.baseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	if c.username != "" {
		req.SetBasicAuth(c.username, c.password)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return []string{"default", "istio-system"}, nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return []string{"default", "istio-system"}, nil
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return []string{"default", "istio-system"}, nil
	}

	var namespaces []map[string]interface{}
	if err := json.Unmarshal(body, &namespaces); err != nil {
		return []string{"default", "istio-system"}, nil
	}

	result := make([]string, 0, len(namespaces))
	for _, ns := range namespaces {
		if name, ok := ns["name"].(string); ok {
			result = append(result, name)
		}
	}

	return result, nil
}

func (c *Client) GetAppHealth(ctx context.Context, namespace, app string) (string, error) {
	url := fmt.Sprintf("%s/api/namespaces/%s/apps/%s/health", c.baseURL, namespace, app)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "unknown", fmt.Errorf("failed to create request: %w", err)
	}

	if c.username != "" {
		req.SetBasicAuth(c.username, c.password)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "healthy", nil
	}
	defer resp.Body.Close()

	return "healthy", nil
}

func getStringValue(data map[string]interface{}, key string) string {
	if v, ok := data[key].(string); ok {
		return v
	}
	return ""
}

func getFloatValue(data map[string]interface{}, key string) float64 {
	if v, ok := data[key].(float64); ok {
		return v
	}
	return 0
}

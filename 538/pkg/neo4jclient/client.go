package neo4jclient

import (
	"context"
	"fmt"
	"time"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
	"k8s-network-policy-recommender/pkg/config"
)

type Client struct {
	driver neo4j.DriverWithContext
}

type PodNode struct {
	Name        string            `json:"name"`
	Namespace   string            `json:"namespace"`
	Labels      map[string]string `json:"labels"`
	IP          string            `json:"ip"`
	PodSelector map[string]string `json:"podSelector"`
}

type FlowEdge struct {
	SourceName      string `json:"sourceName"`
	SourceNamespace string `json:"sourceNamespace"`
	DestName        string `json:"destName"`
	DestNamespace   string `json:"destNamespace"`
	Protocol        string `json:"protocol"`
	Port            int32  `json:"port"`
	Count           int64  `json:"count"`
	LastSeen        string `json:"lastSeen"`
}

func NewClient(cfg config.Neo4jConfig) (*Client, error) {
	driver, err := neo4j.NewDriverWithContext(
		cfg.URI,
		neo4j.BasicAuth(cfg.Username, cfg.Password, ""),
	)
	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := driver.VerifyConnectivity(ctx); err != nil {
		return nil, err
	}

	return &Client{driver: driver}, nil
}

func (c *Client) Close() error {
	return c.driver.Close(context.Background())
}

func (c *Client) InitSchema(ctx context.Context) error {
	session := c.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	queries := []string{
		`CREATE CONSTRAINT pod_name IF NOT EXISTS FOR (p:Pod) REQUIRE p.name IS UNIQUE`,
		`CREATE INDEX pod_namespace IF NOT EXISTS FOR (p:Pod) ON (p.namespace)`,
		`CREATE INDEX flow_last_seen IF NOT EXISTS FOR ()-[f:FLOWS_TO]-() ON (f.lastSeen)`,
	}

	for _, q := range queries {
		_, err := session.Run(ctx, q, nil)
		if err != nil {
			return fmt.Errorf("failed to execute query '%s': %w", q, err)
		}
	}

	return nil
}

func (c *Client) AddPod(ctx context.Context, pod PodNode) error {
	session := c.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.Run(ctx, `
		MERGE (p:Pod {name: $name, namespace: $namespace})
		SET p.ip = $ip,
		    p.labels = $labels,
		    p.podSelector = $podSelector,
		    p.lastUpdated = datetime()
		RETURN p
	`, map[string]any{
		"name":        pod.Name,
		"namespace":   pod.Namespace,
		"ip":          pod.IP,
		"labels":      pod.Labels,
		"podSelector": pod.PodSelector,
	})

	return err
}

func (c *Client) AddFlow(ctx context.Context, flow FlowEdge) error {
	session := c.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.Run(ctx, `
		MERGE (src:Pod {name: $srcName, namespace: $srcNs})
		MERGE (dst:Pod {name: $dstName, namespace: $dstNs})
		MERGE (src)-[f:FLOWS_TO {protocol: $protocol, port: $port}]->(dst)
		SET f.count = COALESCE(f.count, 0) + 1,
		    f.lastSeen = $lastSeen
	`, map[string]any{
		"srcName":  flow.SourceName,
		"srcNs":    flow.SourceNamespace,
		"dstName":  flow.DestName,
		"dstNs":    flow.DestNamespace,
		"protocol": flow.Protocol,
		"port":     flow.Port,
		"lastSeen": flow.LastSeen,
	})

	return err
}

func (c *Client) GetTopology(ctx context.Context, namespace string) ([]PodNode, []FlowEdge, error) {
	session := c.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	var pods []PodNode
	var flows []FlowEdge

	podQuery := `
		MATCH (p:Pod)
		WHERE $namespace = '' OR p.namespace = $namespace
		RETURN p.name AS name, p.namespace AS namespace, p.ip AS ip, p.labels AS labels
	`
	podResult, err := session.Run(ctx, podQuery, map[string]any{"namespace": namespace})
	if err != nil {
		return nil, nil, err
	}

	for podResult.Next(ctx) {
		record := podResult.Record()
		pod := PodNode{
			Name:      record.GetByIndex(0).(string),
			Namespace: record.GetByIndex(1).(string),
			IP:        record.GetByIndex(2).(string),
		}
		if labels, ok := record.GetByIndex(3).(map[string]string); ok {
			pod.Labels = labels
		}
		pods = append(pods, pod)
	}

	flowQuery := `
		MATCH (src:Pod)-[f:FLOWS_TO]->(dst:Pod)
		WHERE $namespace = '' OR src.namespace = $namespace OR dst.namespace = $namespace
		RETURN src.name, src.namespace, dst.name, dst.namespace, f.protocol, f.port, f.count, f.lastSeen
	`
	flowResult, err := session.Run(ctx, flowQuery, map[string]any{"namespace": namespace})
	if err != nil {
		return nil, nil, err
	}

	for flowResult.Next(ctx) {
		record := flowResult.Record()
		flow := FlowEdge{
			SourceName:      record.GetByIndex(0).(string),
			SourceNamespace: record.GetByIndex(1).(string),
			DestName:        record.GetByIndex(2).(string),
			DestNamespace:   record.GetByIndex(3).(string),
			Protocol:        record.GetByIndex(4).(string),
		}
		if port, ok := record.GetByIndex(5).(int64); ok {
			flow.Port = int32(port)
		}
		if count, ok := record.GetByIndex(6).(int64); ok {
			flow.Count = count
		}
		if lastSeen, ok := record.GetByIndex(7).(string); ok {
			flow.LastSeen = lastSeen
		}
		flows = append(flows, flow)
	}

	return pods, flows, nil
}

func (c *Client) GetFlowsByNamespace(ctx context.Context, namespace string) ([]FlowEdge, error) {
	session := c.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	var flows []FlowEdge

	query := `
		MATCH (src:Pod)-[f:FLOWS_TO]->(dst:Pod)
		WHERE src.namespace = $namespace AND dst.namespace = $namespace
		RETURN src.name, src.namespace, dst.name, dst.namespace, f.protocol, f.port, f.count
	`

	result, err := session.Run(ctx, query, map[string]any{"namespace": namespace})
	if err != nil {
		return nil, err
	}

	for result.Next(ctx) {
		record := result.Record()
		flow := FlowEdge{
			SourceName:      record.GetByIndex(0).(string),
			SourceNamespace: record.GetByIndex(1).(string),
			DestName:        record.GetByIndex(2).(string),
			DestNamespace:   record.GetByIndex(3).(string),
			Protocol:        record.GetByIndex(4).(string),
		}
		if port, ok := record.GetByIndex(5).(int64); ok {
			flow.Port = int32(port)
		}
		if count, ok := record.GetByIndex(6).(int64); ok {
			flow.Count = count
		}
		flows = append(flows, flow)
	}

	return flows, nil
}

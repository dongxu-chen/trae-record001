package dependency

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"
)

type ResourceType string

const (
	ResourceTypeEC2       ResourceType = "ec2"
	ResourceTypeRDS       ResourceType = "rds"
	ResourceTypeS3        ResourceType = "s3"
	ResourceTypeVPC       ResourceType = "vpc"
	ResourceTypeSubnet    ResourceType = "subnet"
	ResourceTypeSecurityGroup ResourceType = "security_group"
	ResourceTypeEBS       ResourceType = "ebs"
	ResourceTypeEIP       ResourceType = "eip"
	ResourceTypeELB       ResourceType = "elb"
	ResourceTypeRouteTable ResourceType = "route_table"
	ResourceTypeIAMRole   ResourceType = "iam_role"
	ResourceTypeKMSKey    ResourceType = "kms_key"
	ResourceTypeSnapshot  ResourceType = "snapshot"
)

type Resource struct {
	ID         string                 `json:"id"`
	Type       ResourceType           `json:"type"`
	Name       string                 `json:"name"`
	Provider   string                 `json:"provider"`
	Region     string                 `json:"region"`
	Attributes map[string]interface{} `json:"attributes"`
	Tags       map[string]string      `json:"tags"`
}

type DependencyType string

const (
	DependencyTypeNetwork     DependencyType = "network"
	DependencyTypeStorage     DependencyType = "storage"
	DependencyTypeSecurity    DependencyType = "security"
	DependencyTypeCompute     DependencyType = "compute"
	DependencyTypeDatabase    DependencyType = "database"
	DependencyTypeLoadBalancing DependencyType = "load_balancing"
	DependencyTypeIAM         DependencyType = "iam"
)

type Dependency struct {
	FromID   string         `json:"from_id"`
	ToID     string         `json:"to_id"`
	Type     DependencyType `json:"type"`
	Strength int            `json:"strength"`
	Reason   string         `json:"reason"`
}

type DependencyGraph struct {
	Resources   map[string]*Resource   `json:"resources"`
	Dependencies []Dependency          `json:"dependencies"`
	Edges       map[string][]string    `json:"edges"`
	ReverseEdges map[string][]string   `json:"reverse_edges"`
	mu          sync.RWMutex
}

type AnalysisResult struct {
	RootResources    []*Resource          `json:"root_resources"`
	AllResources     []*Resource          `json:"all_resources"`
	Dependencies     []Dependency         `json:"dependencies"`
	MigrationOrder   []string             `json:"migration_order"`
	Warning          []string             `json:"warnings"`
	CircularDeps     [][]string           `json:"circular_deps"`
}

type DependencyAnalyzer struct {
	providers map[string]CloudProvider
}

type CloudProvider interface {
	ListResources(ctx context.Context, types []ResourceType) ([]*Resource, error)
	GetResourceDependencies(ctx context.Context, resource *Resource) ([]Dependency, error)
}

func NewDependencyAnalyzer() *DependencyAnalyzer {
	return &DependencyAnalyzer{
		providers: make(map[string]CloudProvider),
	}
}

func (da *DependencyAnalyzer) RegisterProvider(name string, provider CloudProvider) {
	da.providers[name] = provider
}

func (da *DependencyAnalyzer) Analyze(ctx context.Context, provider string, targetResources []*Resource) (*AnalysisResult, error) {
	graph := &DependencyGraph{
		Resources:    make(map[string]*Resource),
		Edges:        make(map[string][]string),
		ReverseEdges: make(map[string][]string),
	}

	for _, res := range targetResources {
		graph.AddResource(res)
	}

	visited := make(map[string]bool)
	queue := make([]string, 0, len(targetResources))
	for _, res := range targetResources {
		queue = append(queue, res.ID)
	}

	prov, ok := da.providers[provider]
	if !ok {
		prov = &mockProvider{}
	}

	for len(queue) > 0 {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		resID := queue[0]
		queue = queue[1:]

		if visited[resID] {
			continue
		}
		visited[resID] = true

		res := graph.Resources[resID]
		if res == nil {
			continue
		}

		deps, err := prov.GetResourceDependencies(ctx, res)
		if err != nil {
			continue
		}

		for _, dep := range deps {
			graph.AddDependency(dep)
			if !visited[dep.ToID] {
				depRes, err := da.findResource(ctx, prov, dep.ToID)
				if err == nil && depRes != nil {
					graph.AddResource(depRes)
					queue = append(queue, dep.ToID)
				}
			}
		}
	}

	return graph.Analyze(), nil
}

func (g *DependencyGraph) AddResource(res *Resource) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.Resources[res.ID] = res
}

func (g *DependencyGraph) AddDependency(dep Dependency) {
	g.mu.Lock()
	defer g.mu.Unlock()

	g.Dependencies = append(g.Dependencies, dep)

	if _, ok := g.Edges[dep.FromID]; !ok {
		g.Edges[dep.FromID] = make([]string, 0)
	}
	g.Edges[dep.FromID] = append(g.Edges[dep.FromID], dep.ToID)

	if _, ok := g.ReverseEdges[dep.ToID]; !ok {
		g.ReverseEdges[dep.ToID] = make([]string, 0)
	}
	g.ReverseEdges[dep.ToID] = append(g.ReverseEdges[dep.ToID], dep.FromID)
}

func (g *DependencyGraph) Analyze() *AnalysisResult {
	g.mu.RLock()
	defer g.mu.RUnlock()

	result := &AnalysisResult{
		AllResources: make([]*Resource, 0, len(g.Resources)),
		Dependencies: g.Dependencies,
		Warning:      make([]string, 0),
	}

	for _, res := range g.Resources {
		result.AllResources = append(result.AllResources, res)
	}

	result.RootResources = g.findRootResources()
	result.CircularDeps = g.detectCircularDependencies()
	result.MigrationOrder = g.topologicalSort()

	if len(result.CircularDeps) > 0 {
		result.Warning = append(result.Warning,
			fmt.Sprintf("检测到 %d 个循环依赖，可能需要手动处理", len(result.CircularDeps)))
	}

	return result
}

func (g *DependencyGraph) findRootResources() []*Resource {
	roots := make([]*Resource, 0)
	for id, res := range g.Resources {
		if _, ok := g.ReverseEdges[id]; !ok || len(g.ReverseEdges[id]) == 0 {
			roots = append(roots, res)
		}
	}
	return roots
}

func (g *DependencyGraph) detectCircularDependencies() [][]string {
	visited := make(map[string]bool)
	recStack := make(map[string]bool)
	circularDeps := make([][]string, 0)

	var dfs func(string, []string)
	dfs = func(node string, path []string) {
		visited[node] = true
		recStack[node] = true
		path = append(path, node)

		for _, neighbor := range g.Edges[node] {
			if !visited[neighbor] {
				dfs(neighbor, path)
			} else if recStack[neighbor] {
				cycle := make([]string, 0)
				for i := len(path) - 1; i >= 0; i-- {
					cycle = append([]string{path[i]}, cycle...)
					if path[i] == neighbor {
						break
					}
				}
				circularDeps = append(circularDeps, cycle)
			}
		}

		recStack[node] = false
	}

	for id := range g.Resources {
		if !visited[id] {
			dfs(id, []string{})
		}
	}

	return circularDeps
}

func (g *DependencyGraph) topologicalSort() []string {
	inDegree := make(map[string]int)
	for id := range g.Resources {
		inDegree[id] = 0
	}

	for _, deps := range g.Edges {
		for _, dep := range deps {
			inDegree[dep]++
		}
	}

	queue := make([]string, 0)
	for id, degree := range inDegree {
		if degree == 0 {
			queue = append(queue, id)
		}
	}

	sort.Strings(queue)

	result := make([]string, 0, len(g.Resources))
	for len(queue) > 0 {
		sort.Strings(queue)
		node := queue[0]
		queue = queue[1:]
		result = append(result, node)

		for _, neighbor := range g.Edges[node] {
			inDegree[neighbor]--
			if inDegree[neighbor] == 0 {
				queue = append(queue, neighbor)
			}
		}
	}

	return result
}

func (da *DependencyAnalyzer) findResource(ctx context.Context, prov CloudProvider, id string) (*Resource, error) {
	resources, err := prov.ListResources(ctx, nil)
	if err != nil {
		return nil, err
	}

	for _, res := range resources {
		if res.ID == id {
			return res, nil
		}
	}

	return &Resource{
		ID:   id,
		Type: guessResourceType(id),
		Name: id,
	}, nil
}

func guessResourceType(id string) ResourceType {
	switch {
	case strings.HasPrefix(id, "i-"):
		return ResourceTypeEC2
	case strings.HasPrefix(id, "vpc-"):
		return ResourceTypeVPC
	case strings.HasPrefix(id, "subnet-"):
		return ResourceTypeSubnet
	case strings.HasPrefix(id, "sg-"):
		return ResourceTypeSecurityGroup
	case strings.HasPrefix(id, "vol-"):
		return ResourceTypeEBS
	case strings.HasPrefix(id, "eipalloc-"):
		return ResourceTypeEIP
	case strings.HasPrefix(id, "elb-") || strings.HasPrefix(id, "arn:aws:elasticloadbalancing"):
		return ResourceTypeELB
	default:
		return ResourceTypeEC2
	}
}

type mockProvider struct{}

func (m *mockProvider) ListResources(ctx context.Context, types []ResourceType) ([]*Resource, error) {
	return []*Resource{}, nil
}

func (m *mockProvider) GetResourceDependencies(ctx context.Context, res *Resource) ([]Dependency, error) {
	deps := make([]Dependency, 0)

	switch res.Type {
	case ResourceTypeEC2:
		if vpcID, ok := res.Attributes["vpc_id"].(string); ok && vpcID != "" {
			deps = append(deps, Dependency{
				FromID: res.ID,
				ToID:   vpcID,
				Type:   DependencyTypeNetwork,
				Reason: "EC2实例运行在VPC中",
			})
		}
		if sgIDs, ok := res.Attributes["security_group_ids"].([]string); ok {
			for _, sgID := range sgIDs {
				deps = append(deps, Dependency{
					FromID: res.ID,
					ToID:   sgID,
					Type:   DependencyTypeSecurity,
					Reason: "EC2实例关联安全组",
				})
			}
		}
		if volIDs, ok := res.Attributes["volume_ids"].([]string); ok {
			for _, volID := range volIDs {
				deps = append(deps, Dependency{
					FromID: res.ID,
					ToID:   volID,
					Type:   DependencyTypeStorage,
					Reason: "EC2实例挂载EBS卷",
				})
			}
		}
	}

	return deps, nil
}

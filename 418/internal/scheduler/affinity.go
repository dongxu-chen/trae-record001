package scheduler

import (
	"fmt"
	"hash/fnv"
	"sort"
	"strings"
	"time"
)

type NodeAffinity struct {
	NodeName   string            `json:"node_name"`
	Selector   map[string]string `json:"selector"`
	Weight     int               `json:"weight"`
	PreferZone string            `json:"prefer_zone"`
}

type TopologyKey string

const (
	TopologyZone     TopologyKey = "topology.kubernetes.io/zone"
	TopologyRegion   TopologyKey = "topology.kubernetes.io/region"
	TopologyNode     TopologyKey = "kubernetes.io/hostname"
	FunctionLabel    TopologyKey = "coldstart.io/function"
	PreferWarmLabel  TopologyKey = "coldstart.io/warm-prefer"
)

type Node struct {
	Name       string            `json:"name"`
	Zone       string            `json:"zone"`
	Region     string            `json:"region"`
	Labels     map[string]string `json:"labels"`
	Capacity   Resource          `json:"capacity"`
	Allocatable Resource          `json:"allocatable"`
	Used       Resource          `json:"used"`
}

type Resource struct {
	CPUMillis float64 `json:"cpu_millis"`
	MemoryMB  uint64  `json:"memory_mb"`
}

type FunctionTopology struct {
	Function    string
	Runtime     string
	PreferZones []string
	NodeWeights map[string]int
	PinNode     string
}

type AffinityEngine struct {
	nodes map[string]*Node
}

func NewAffinityEngine(nodes []*Node) *AffinityEngine {
	m := make(map[string]*Node, len(nodes))
	for _, n := range nodes {
		m[n.Name] = n
	}
	return &AffinityEngine{nodes: m}
}

func (e *AffinityEngine) AddNode(n *Node) { e.nodes[n.Name] = n }

func (e *AffinityEngine) ScoreNodes(fn FunctionTopology) ([]NodeAffinity, error) {
	if len(e.nodes) == 0 {
		return nil, fmt.Errorf("no nodes available")
	}
	type scored struct {
		name  string
		node  *Node
		score int
	}
	var list []scored
	for _, n := range e.nodes {
		s := 0
		if n.Zone != "" {
			for _, z := range fn.PreferZones {
				if n.Zone == z {
					s += 100
				}
			}
		}
		if fn.NodeWeights != nil {
			if w, ok := fn.NodeWeights[n.Name]; ok {
				s += w
			}
		}
		if fn.PinNode != "" && fn.PinNode == n.Name {
			s += 1000
		}
		if v, ok := n.Labels[string(PreferWarmLabel)]; ok && v == "true" {
			s += 50
		}
		if fn.Runtime != "" {
			key := "coldstart.io/runtime-" + fn.Runtime
			if v, ok := n.Labels[key]; ok && v == "true" {
				s += 80
			}
		}
		list = append(list, scored{name: n.Name, node: n, score: s})
	}
	sort.SliceStable(list, func(i, k int) bool { return list[i].score > list[k].score })
	var out []NodeAffinity
	for _, s := range list {
		out = append(out, NodeAffinity{
			NodeName:   s.name,
			Selector:   s.node.Labels,
			Weight:     s.score,
			PreferZone: s.node.Zone,
		})
	}
	return out, nil
}

func (e *AffinityEngine) PickPreloadNodes(fn FunctionTopology, count int) ([]NodeAffinity, error) {
	all, err := e.ScoreNodes(fn)
	if err != nil {
		return nil, err
	}
	if count <= 0 || count > len(all) {
		count = len(all)
	}
	return all[:count], nil
}

func (e *AffinityEngine) PlanPreloadSchedule(function, imageRef string, targetNodes []NodeAffinity) []PreloadTask {
	var tasks []PreloadTask
	for _, n := range targetNodes {
		tasks = append(tasks, PreloadTask{
			TaskID:    taskID(function, imageRef, n.NodeName),
			Function:  function,
			ImageRef:  imageRef,
			NodeName:  n.NodeName,
			Zone:      n.PreferZone,
			Affinity:  n,
			CreatedAt: time.Now(),
		})
	}
	return tasks
}

type PreloadTask struct {
	TaskID     string        `json:"task_id"`
	Function   string        `json:"function"`
	ImageRef   string        `json:"image_ref"`
	NodeName   string        `json:"node_name"`
	Zone       string        `json:"zone"`
	Affinity   NodeAffinity  `json:"affinity"`
	CreatedAt  time.Time     `json:"created_at"`
	StartedAt  time.Time     `json:"started_at,omitempty"`
	FinishedAt time.Time     `json:"finished_at,omitempty"`
	Status     string        `json:"status"`
	Error      string        `json:"error,omitempty"`
	Duration   time.Duration `json:"duration_ms"`
}

func taskID(function, image, node string) string {
	h := fnv.New64a()
	h.Write([]byte(function + "|" + image + "|" + node))
	return fmt.Sprintf("preload-%x", h.Sum64())
}

type PreloadPlan struct {
	Function string       `json:"function"`
	ImageRef string       `json:"image_ref"`
	Tasks    []PreloadTask `json:"tasks"`
}

func BuildPreloadPlan(function, imageRef string, topo FunctionTopology, engine *AffinityEngine, replicas int) (*PreloadPlan, error) {
	targets, err := engine.PickPreloadNodes(topo, replicas)
	if err != nil {
		return nil, err
	}
	return &PreloadPlan{
		Function: function,
		ImageRef: imageRef,
		Tasks:    engine.PlanPreloadSchedule(function, imageRef, targets),
	}, nil
}

func AffinityForFunction(function, runtime string, preferZones []string, pinNode string) FunctionTopology {
	return FunctionTopology{
		Function:    function,
		Runtime:     runtime,
		PreferZones: preferZones,
		NodeWeights: map[string]int{},
		PinNode:     pinNode,
	}
}

func AffinityLabelSelector(function, runtime string) map[string]string {
	return map[string]string{
		"coldstart.io/function":  sanitizeLabel(function),
		"coldstart.io/runtime":   sanitizeLabel(runtime),
		"coldstart.io/pre-warm":  "true",
	}
}

func sanitizeLabel(s string) string {
	s = strings.ToLower(s)
	var b strings.Builder
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' || r == '_' || r == '.' {
			b.WriteRune(r)
		} else {
			b.WriteRune('-')
		}
	}
	out := b.String()
	if len(out) > 63 {
		out = out[:63]
	}
	return out
}

package dag

import (
	"errors"
	"fmt"
	"strings"
)

type Graph struct {
	nodes    map[string]bool
	edges    map[string][]string
	inDegree map[string]int
}

func NewGraph() *Graph {
	return &Graph{
		nodes:    make(map[string]bool),
		edges:    make(map[string][]string),
		inDegree: make(map[string]int),
	}
}

func (g *Graph) AddNode(node string) {
	if !g.nodes[node] {
		g.nodes[node] = true
		g.inDegree[node] = 0
	}
}

func (g *Graph) AddEdge(from, to string) error {
	if !g.nodes[from] || !g.nodes[to] {
		return errors.New("node does not exist")
	}

	for _, existing := range g.edges[from] {
		if existing == to {
			return nil
		}
	}

	g.edges[from] = append(g.edges[from], to)
	g.inDegree[to]++

	return nil
}

func (g *Graph) TopologicalSort() ([]string, error) {
	result := make([]string, 0, len(g.nodes))
	queue := make([]string, 0)
	inDegreeCopy := make(map[string]int)

	for node, degree := range g.inDegree {
		inDegreeCopy[node] = degree
		if degree == 0 {
			queue = append(queue, node)
		}
	}

	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		result = append(result, node)

		for _, neighbor := range g.edges[node] {
			inDegreeCopy[neighbor]--
			if inDegreeCopy[neighbor] == 0 {
				queue = append(queue, neighbor)
			}
		}
	}

	if len(result) != len(g.nodes) {
		return nil, errors.New("graph has a cycle")
	}

	return result, nil
}

func (g *Graph) GetDependents(node string) []string {
	return g.edges[node]
}

func (g *Graph) GetDependencies(node string) []string {
	deps := make([]string, 0)
	for from, tos := range g.edges {
		for _, to := range tos {
			if to == node {
				deps = append(deps, from)
			}
		}
	}
	return deps
}

func (g *Graph) HasNode(node string) bool {
	return g.nodes[node]
}

func (g *Graph) NodeCount() int {
	return len(g.nodes)
}

func (g *Graph) EdgeCount() int {
	count := 0
	for _, edges := range g.edges {
		count += len(edges)
	}
	return count
}

type TaskDependencyGraph struct {
	*Graph
	taskMap map[string]interface{}
}

func NewTaskDependencyGraph() *TaskDependencyGraph {
	return &TaskDependencyGraph{
		Graph:   NewGraph(),
		taskMap: make(map[string]interface{}),
	}
}

func (g *TaskDependencyGraph) AddTask(taskID string, dependencies []string, task interface{}) error {
	g.AddNode(taskID)
	g.taskMap[taskID] = task

	for _, dep := range dependencies {
		dep = strings.TrimSpace(dep)
		if dep == "" {
			continue
		}
		g.AddNode(dep)
		if err := g.AddEdge(dep, taskID); err != nil {
			return err
		}
	}

	return nil
}

func (g *TaskDependencyGraph) GetExecutionOrder() ([]string, error) {
	return g.TopologicalSort()
}

func (g *TaskDependencyGraph) GetTask(taskID string) interface{} {
	return g.taskMap[taskID]
}

func (g *TaskDependencyGraph) GetReadyTasks(completedTasks map[string]bool) []string {
	ready := make([]string, 0)

	for node := range g.nodes {
		if completedTasks[node] {
			continue
		}

		deps := g.GetDependencies(node)
		allCompleted := true
		for _, dep := range deps {
			if !completedTasks[dep] {
				allCompleted = false
				break
			}
		}

		if allCompleted {
			ready = append(ready, node)
		}
	}

	return ready
}

func (g *TaskDependencyGraph) ValidateNoCycles() error {
	_, err := g.TopologicalSort()
	return err
}

func BuildTaskGraphFromDependencies(taskDeps map[string][]string) (*TaskDependencyGraph, error) {
	graph := NewTaskDependencyGraph()

	for taskID, deps := range taskDeps {
		if err := graph.AddTask(taskID, deps, nil); err != nil {
			return nil, fmt.Errorf("failed to add task %s: %w", taskID, err)
		}
	}

	if err := graph.ValidateNoCycles(); err != nil {
		return nil, err
	}

	return graph, nil
}

package dag

import (
	"fmt"
	"os"
	"sort"

	"gopkg.in/yaml.v3"
)

func ParsePipelineFromFile(path string) (*Pipeline, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read pipeline file: %w", err)
	}
	return ParsePipeline(data)
}

func ParsePipeline(data []byte) (*Pipeline, error) {
	var pipeline Pipeline
	if err := yaml.Unmarshal(data, &pipeline); err != nil {
		return nil, fmt.Errorf("failed to parse pipeline yaml: %w", err)
	}

	if err := validatePipeline(&pipeline); err != nil {
		return nil, err
	}

	for i := range pipeline.Tasks {
		task := &pipeline.Tasks[i]
		if task.Resources.CPU == 0 {
			task.Resources.CPU = pipeline.Resources.CPU
		}
		if task.Resources.Memory == 0 {
			task.Resources.Memory = pipeline.Resources.Memory
		}
		if task.MaxRetries == 0 {
			task.MaxRetries = 3
		}
		if task.RetryDelay == 0 {
			task.RetryDelay = 5
		}
		if task.Priority == 0 {
			task.Priority = 5
		}
		task.Status = TaskStatusPending
	}

	return &pipeline, nil
}

func validatePipeline(pipeline *Pipeline) error {
	if pipeline.ID == "" {
		return fmt.Errorf("pipeline ID is required")
	}
	if len(pipeline.Tasks) == 0 {
		return fmt.Errorf("pipeline must have at least one task")
	}

	taskIDs := make(map[string]bool)
	for _, task := range pipeline.Tasks {
		if task.ID == "" {
			return fmt.Errorf("task ID is required")
		}
		if taskIDs[task.ID] {
			return fmt.Errorf("duplicate task ID: %s", task.ID)
		}
		taskIDs[task.ID] = true
	}

	for _, task := range pipeline.Tasks {
		for _, dep := range task.DependsOn {
			if !taskIDs[dep] {
				return fmt.Errorf("task %s depends on non-existent task %s", task.ID, dep)
			}
		}
	}

	return nil
}

func BuildDAG(pipeline *Pipeline) (*DAG, error) {
	dag := &DAG{
		Nodes:           make(map[string]*Node),
		Tasks:           make(map[string]*Task),
		topoPosition:    make(map[string]int),
		descendantCache: make(map[string]map[string]bool),
		ancestorCache:   make(map[string]map[string]bool),
		cacheValid:      false,
	}

	for i := range pipeline.Tasks {
		task := &pipeline.Tasks[i]
		dag.Nodes[task.ID] = &Node{
			Task:    task,
			OutEdges: make([]*Node, 0),
			InEdges:  make([]*Node, 0),
		}
		dag.Tasks[task.ID] = task
	}

	for i := range pipeline.Tasks {
		task := &pipeline.Tasks[i]
		node := dag.Nodes[task.ID]

		for _, depID := range task.DependsOn {
			depNode := dag.Nodes[depID]
			depNode.OutEdges = append(depNode.OutEdges, node)
			node.InEdges = append(node.InEdges, depNode)
			node.InDegree++
		}
	}

	if err := detectCycle(dag); err != nil {
		return nil, err
	}

	if err := dag.buildTopoCache(); err != nil {
		return nil, err
	}

	return dag, nil
}

func detectCycle(dag *DAG) error {
	visited := make(map[string]bool)
	recStack := make(map[string]bool)

	var dfs func(nodeID string) bool
	dfs = func(nodeID string) bool {
		visited[nodeID] = true
		recStack[nodeID] = true

		node := dag.Nodes[nodeID]
		for _, neighbor := range node.OutEdges {
			neighborID := neighbor.Task.ID
			if !visited[neighborID] {
				if dfs(neighborID) {
					return true
				}
			} else if recStack[neighborID] {
				return true
			}
		}

		recStack[nodeID] = false
		return false
	}

	for nodeID := range dag.Nodes {
		if !visited[nodeID] {
			if dfs(nodeID) {
				return fmt.Errorf("cycle detected in DAG")
			}
		}
	}

	return nil
}

func (d *DAG) GetReadyTasks() []*Task {
	ready := make([]*Task, 0)
	for _, node := range d.Nodes {
		if node.Task.Status == TaskStatusPending && node.InDegree == 0 {
			ready = append(ready, node.Task)
		}
	}
	return ready
}

func (d *DAG) MarkTaskComplete(taskID string) {
	node := d.Nodes[taskID]
	if node == nil {
		return
	}
	node.Task.Status = TaskStatusSuccess

	for _, neighbor := range node.OutEdges {
		neighbor.InDegree--
	}
}

func (d *DAG) MarkTaskFailed(taskID string, retry bool) {
	node := d.Nodes[taskID]
	if node == nil {
		return
	}

	if retry {
		node.Task.Status = TaskStatusRetry
		node.Task.RetryCount++
	} else {
		node.Task.Status = TaskStatusFailed
		for _, neighbor := range node.OutEdges {
			neighbor.Task.Status = TaskStatusSkipped
		}
	}
}

func (d *DAG) HasPendingTasks() bool {
	for _, task := range d.Tasks {
		if task.Status == TaskStatusPending || task.Status == TaskStatusRunning || task.Status == TaskStatusRetry {
			return true
		}
	}
	return false
}

func (d *DAG) AllTasksCompleted() bool {
	for _, task := range d.Tasks {
		if task.Status != TaskStatusSuccess && task.Status != TaskStatusSkipped {
			return false
		}
	}
	return true
}

func (d *DAG) GetFailedTasks() []*Task {
	failed := make([]*Task, 0)
	for _, task := range d.Tasks {
		if task.Status == TaskStatusFailed {
			failed = append(failed, task)
		}
	}
	return failed
}

func (d *DAG) buildTopoCache() error {
	topoOrder, err := d.topologicalSortInternal()
	if err != nil {
		return err
	}

	d.topoOrder = topoOrder
	for i, taskID := range topoOrder {
		d.topoPosition[taskID] = i
	}

	for _, taskID := range d.topoOrder {
		d.descendantCache[taskID] = make(map[string]bool)
		d.ancestorCache[taskID] = make(map[string]bool)
	}

	for i := len(d.topoOrder) - 1; i >= 0; i-- {
		taskID := d.topoOrder[i]
		node := d.Nodes[taskID]
		for _, outNode := range node.OutEdges {
			outID := outNode.Task.ID
			d.descendantCache[taskID][outID] = true
			for descID := range d.descendantCache[outID] {
				d.descendantCache[taskID][descID] = true
			}
		}
	}

	for i := 0; i < len(d.topoOrder); i++ {
		taskID := d.topoOrder[i]
		node := d.Nodes[taskID]
		for _, inNode := range node.InEdges {
			inID := inNode.Task.ID
			d.ancestorCache[taskID][inID] = true
			for ancID := range d.ancestorCache[inID] {
				d.ancestorCache[taskID][ancID] = true
			}
		}
	}

	d.cacheValid = true
	return nil
}

func (d *DAG) topologicalSortInternal() ([]string, error) {
	inDegree := make(map[string]int)
	for id, node := range d.Nodes {
		inDegree[id] = node.InDegree
	}

	queue := make([]string, 0)
	for id, deg := range inDegree {
		if deg == 0 {
			queue = append(queue, id)
		}
	}

	sort.Strings(queue)

	result := make([]string, 0)
	for len(queue) > 0 {
		nodeID := queue[0]
		queue = queue[1:]
		result = append(result, nodeID)

		node := d.Nodes[nodeID]
		for _, neighbor := range node.OutEdges {
			neighborID := neighbor.Task.ID
			inDegree[neighborID]--
			if inDegree[neighborID] == 0 {
				queue = append(queue, neighborID)
				sort.Strings(queue)
			}
		}
	}

	if len(result) != len(d.Nodes) {
		return nil, fmt.Errorf("failed to perform topological sort, possible cycle")
	}

	return result, nil
}

func (d *DAG) IsDescendant(taskID, descendantID string) (bool, error) {
	if !d.cacheValid {
		if err := d.buildTopoCache(); err != nil {
			return false, err
		}
	}

	if descendants, ok := d.descendantCache[taskID]; ok {
		return descendants[descendantID], nil
	}
	return false, fmt.Errorf("task %s not found", taskID)
}

func (d *DAG) IsAncestor(taskID, ancestorID string) (bool, error) {
	if !d.cacheValid {
		if err := d.buildTopoCache(); err != nil {
			return false, err
		}
	}

	if ancestors, ok := d.ancestorCache[taskID]; ok {
		return ancestors[ancestorID], nil
	}
	return false, fmt.Errorf("task %s not found", taskID)
}

func (d *DAG) AreDependent(taskID1, taskID2 string) (bool, error) {
	if !d.cacheValid {
		if err := d.buildTopoCache(); err != nil {
			return false, err
		}
	}

	isDesc, _ := d.IsDescendant(taskID1, taskID2)
	if isDesc {
		return true, nil
	}

	isAnc, _ := d.IsAncestor(taskID1, taskID2)
	return isAnc, nil
}

func (d *DAG) GetTopoOrder() ([]string, error) {
	if !d.cacheValid {
		if err := d.buildTopoCache(); err != nil {
			return nil, err
		}
	}
	result := make([]string, len(d.topoOrder))
	copy(result, d.topoOrder)
	return result, nil
}

func (d *DAG) GetTopoPosition(taskID string) (int, error) {
	if !d.cacheValid {
		if err := d.buildTopoCache(); err != nil {
			return -1, err
		}
	}

	if pos, ok := d.topoPosition[taskID]; ok {
		return pos, nil
	}
	return -1, fmt.Errorf("task %s not found", taskID)
}

func (d *DAG) InvalidateCache() {
	d.cacheValid = false
}

func (d *DAG) CanRunParallel(taskID1, taskID2 string) (bool, error) {
	dep, err := d.AreDependent(taskID1, taskID2)
	if err != nil {
		return false, err
	}
	return !dep, nil
}

func (d *DAG) GetDescendants(taskID string) ([]string, error) {
	if !d.cacheValid {
		if err := d.buildTopoCache(); err != nil {
			return nil, err
		}
	}

	descendants, ok := d.descendantCache[taskID]
	if !ok {
		return nil, fmt.Errorf("task %s not found", taskID)
	}

	result := make([]string, 0, len(descendants))
	for id := range descendants {
		result = append(result, id)
	}
	sort.Strings(result)
	return result, nil
}

func (d *DAG) GetAncestors(taskID string) ([]string, error) {
	if !d.cacheValid {
		if err := d.buildTopoCache(); err != nil {
			return nil, err
		}
	}

	ancestors, ok := d.ancestorCache[taskID]
	if !ok {
		return nil, fmt.Errorf("task %s not found", taskID)
	}

	result := make([]string, 0, len(ancestors))
	for id := range ancestors {
		result = append(result, id)
	}
	sort.Strings(result)
	return result, nil
}

package dag

import (
	"testing"
	"time"
)

const testPipelineYAML = `
id: test-pipeline
name: Test Pipeline
default_resources:
  cpu: 1.0
  memory: 1024
tasks:
  - id: task-1
    name: Task 1
    image: alpine:latest
    command: ["echo", "task1"]
    priority: 5
    max_retries: 3
    estimated_time: 1m
    resources:
      cpu: 1.0
      memory: 512
  - id: task-2
    name: Task 2
    image: alpine:latest
    command: ["echo", "task2"]
    depends_on:
      - task-1
    priority: 8
    estimated_time: 2m
  - id: task-3
    name: Task 3
    image: alpine:latest
    command: ["echo", "task3"]
    depends_on:
      - task-1
    priority: 10
    estimated_time: 3m
  - id: task-4
    name: Task 4
    image: alpine:latest
    command: ["echo", "task4"]
    depends_on:
      - task-2
      - task-3
    priority: 9
    estimated_time: 1m
`

func TestParsePipeline(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	if pipeline.ID != "test-pipeline" {
		t.Errorf("Expected pipeline ID 'test-pipeline', got '%s'", pipeline.ID)
	}

	if len(pipeline.Tasks) != 4 {
		t.Errorf("Expected 4 tasks, got %d", len(pipeline.Tasks))
	}

	if pipeline.Tasks[0].Resources.CPU != 1.0 {
		t.Errorf("Expected task-1 CPU 1.0, got %.2f", pipeline.Tasks[0].Resources.CPU)
	}

	if pipeline.Tasks[1].MaxRetries != 3 {
		t.Errorf("Expected task-2 MaxRetries 3 (default), got %d", pipeline.Tasks[1].MaxRetries)
	}
}

func TestBuildDAG(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	if len(dag.Nodes) != 4 {
		t.Errorf("Expected 4 nodes, got %d", len(dag.Nodes))
	}

	task1Node := dag.Nodes["task-1"]
	if task1Node.InDegree != 0 {
		t.Errorf("Expected task-1 inDegree 0, got %d", task1Node.InDegree)
	}
	if len(task1Node.OutEdges) != 2 {
		t.Errorf("Expected task-1 to have 2 out edges, got %d", len(task1Node.OutEdges))
	}

	task4Node := dag.Nodes["task-4"]
	if task4Node.InDegree != 2 {
		t.Errorf("Expected task-4 inDegree 2, got %d", task4Node.InDegree)
	}
}

func TestCycleDetection(t *testing.T) {
	cycleYAML := `
id: cycle-pipeline
name: Cycle Test
default_resources:
  cpu: 1.0
  memory: 512
tasks:
  - id: task-a
    name: Task A
    image: alpine:latest
    command: ["echo", "a"]
    depends_on:
      - task-b
  - id: task-b
    name: Task B
    image: alpine:latest
    command: ["echo", "b"]
    depends_on:
      - task-a
`
	pipeline, err := ParsePipeline([]byte(cycleYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	_, err = BuildDAG(pipeline)
	if err == nil {
		t.Error("Expected cycle detection error, got nil")
	}
}

func TestCalculateCriticalPath(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	criticalPath, scheduleInfo, err := dag.CalculateCriticalPath()
	if err != nil {
		t.Fatalf("Failed to calculate critical path: %v", err)
	}

	expectedPath := []string{"task-1", "task-3", "task-4"}
	if len(criticalPath.Path) != len(expectedPath) {
		t.Errorf("Expected critical path length %d, got %d", len(expectedPath), len(criticalPath.Path))
	}

	expectedDuration := 1*time.Minute + 3*time.Minute + 1*time.Minute
	if criticalPath.TotalDuration != expectedDuration {
		t.Errorf("Expected total duration %v, got %v", expectedDuration, criticalPath.TotalDuration)
	}

	task3Info := scheduleInfo["task-3"]
	if !task3Info.IsCritical {
		t.Error("Expected task-3 to be critical")
	}

	task2Info := scheduleInfo["task-2"]
	if task2Info.IsCritical {
		t.Error("Expected task-2 to be non-critical")
	}

	expectedSlack := 1 * time.Minute
	if task2Info.Slack != expectedSlack {
		t.Errorf("Expected task-2 slack %v, got %v", expectedSlack, task2Info.Slack)
	}
}

func TestGetMaxParallelism(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	maxParallel := dag.GetMaxParallelism()
	if maxParallel != 2 {
		t.Errorf("Expected max parallelism 2, got %d", maxParallel)
	}
}

func TestGetReadyTasks(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	ready := dag.GetReadyTasks()
	if len(ready) != 1 {
		t.Errorf("Expected 1 ready task, got %d", len(ready))
	}

	if ready[0].ID != "task-1" {
		t.Errorf("Expected ready task 'task-1', got '%s'", ready[0].ID)
	}
}

func TestMarkTaskComplete(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	dag.MarkTaskComplete("task-1")

	if dag.Tasks["task-1"].Status != TaskStatusSuccess {
		t.Error("Expected task-1 status to be success")
	}

	if dag.Nodes["task-2"].InDegree != 0 {
		t.Errorf("Expected task-2 inDegree 0 after task-1 complete, got %d", dag.Nodes["task-2"].InDegree)
	}

	if dag.Nodes["task-3"].InDegree != 0 {
		t.Errorf("Expected task-3 inDegree 0 after task-1 complete, got %d", dag.Nodes["task-3"].InDegree)
	}

	ready := dag.GetReadyTasks()
	if len(ready) != 2 {
		t.Errorf("Expected 2 ready tasks, got %d", len(ready))
	}
}

func TestMarkTaskFailed(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	dag.MarkTaskComplete("task-1")
	dag.MarkTaskFailed("task-2", false)

	if dag.Tasks["task-2"].Status != TaskStatusFailed {
		t.Error("Expected task-2 status to be failed")
	}

	if dag.Tasks["task-4"].Status != TaskStatusSkipped {
		t.Error("Expected task-4 status to be skipped due to task-2 failure")
	}
}

func TestHasPendingTasks(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	if !dag.HasPendingTasks() {
		t.Error("Expected pending tasks initially")
	}

	for id := range dag.Tasks {
		dag.Tasks[id].Status = TaskStatusSuccess
	}

	if dag.HasPendingTasks() {
		t.Error("Expected no pending tasks after all success")
	}
}

func TestTopoCache(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	if !dag.cacheValid {
		t.Error("Expected cache to be valid after BuildDAG")
	}

	topoOrder, err := dag.GetTopoOrder()
	if err != nil {
		t.Fatalf("Failed to get topo order: %v", err)
	}

	expectedOrder := []string{"task-1", "task-2", "task-3", "task-4"}
	if len(topoOrder) != len(expectedOrder) {
		t.Errorf("Expected topo order length %d, got %d", len(expectedOrder), len(topoOrder))
	}

	if topoOrder[0] != "task-1" {
		t.Errorf("Expected first task 'task-1', got '%s'", topoOrder[0])
	}

	if topoOrder[3] != "task-4" {
		t.Errorf("Expected last task 'task-4', got '%s'", topoOrder[3])
	}

	pos, err := dag.GetTopoPosition("task-3")
	if err != nil {
		t.Fatalf("Failed to get topo position: %v", err)
	}
	if pos < 1 || pos > 2 {
		t.Errorf("Expected task-3 position 1 or 2, got %d", pos)
	}
}

func TestIsDescendant(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	isDesc, err := dag.IsDescendant("task-1", "task-4")
	if err != nil {
		t.Fatalf("Failed to check descendant: %v", err)
	}
	if !isDesc {
		t.Error("Expected task-4 to be descendant of task-1")
	}

	isDesc, err = dag.IsDescendant("task-2", "task-4")
	if err != nil {
		t.Fatalf("Failed to check descendant: %v", err)
	}
	if !isDesc {
		t.Error("Expected task-4 to be descendant of task-2")
	}

	isDesc, err = dag.IsDescendant("task-2", "task-3")
	if err != nil {
		t.Fatalf("Failed to check descendant: %v", err)
	}
	if isDesc {
		t.Error("Expected task-3 to NOT be descendant of task-2")
	}

	isDesc, err = dag.IsDescendant("task-4", "task-1")
	if err != nil {
		t.Fatalf("Failed to check descendant: %v", err)
	}
	if isDesc {
		t.Error("Expected task-1 to NOT be descendant of task-4")
	}
}

func TestIsAncestor(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	isAnc, err := dag.IsAncestor("task-4", "task-1")
	if err != nil {
		t.Fatalf("Failed to check ancestor: %v", err)
	}
	if !isAnc {
		t.Error("Expected task-1 to be ancestor of task-4")
	}

	isAnc, err = dag.IsAncestor("task-3", "task-1")
	if err != nil {
		t.Fatalf("Failed to check ancestor: %v", err)
	}
	if !isAnc {
		t.Error("Expected task-1 to be ancestor of task-3")
	}

	isAnc, err = dag.IsAncestor("task-2", "task-3")
	if err != nil {
		t.Fatalf("Failed to check ancestor: %v", err)
	}
	if isAnc {
		t.Error("Expected task-3 to NOT be ancestor of task-2")
	}
}

func TestAreDependent(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	dep, err := dag.AreDependent("task-1", "task-4")
	if err != nil {
		t.Fatalf("Failed to check dependency: %v", err)
	}
	if !dep {
		t.Error("Expected task-1 and task-4 to be dependent")
	}

	dep, err = dag.AreDependent("task-2", "task-3")
	if err != nil {
		t.Fatalf("Failed to check dependency: %v", err)
	}
	if dep {
		t.Error("Expected task-2 and task-3 to be independent")
	}
}

func TestCanRunParallel(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	canParallel, err := dag.CanRunParallel("task-2", "task-3")
	if err != nil {
		t.Fatalf("Failed to check parallel: %v", err)
	}
	if !canParallel {
		t.Error("Expected task-2 and task-3 can run in parallel")
	}

	canParallel, err = dag.CanRunParallel("task-1", "task-4")
	if err != nil {
		t.Fatalf("Failed to check parallel: %v", err)
	}
	if canParallel {
		t.Error("Expected task-1 and task-4 cannot run in parallel")
	}
}

func TestGetDescendants(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	descendants, err := dag.GetDescendants("task-1")
	if err != nil {
		t.Fatalf("Failed to get descendants: %v", err)
	}
	if len(descendants) != 3 {
		t.Errorf("Expected 3 descendants of task-1, got %d", len(descendants))
	}

	descendants, err = dag.GetDescendants("task-2")
	if err != nil {
		t.Fatalf("Failed to get descendants: %v", err)
	}
	if len(descendants) != 1 || descendants[0] != "task-4" {
		t.Errorf("Expected [task-4] as descendants of task-2, got %v", descendants)
	}
}

func TestInvalidateCache(t *testing.T) {
	pipeline, err := ParsePipeline([]byte(testPipelineYAML))
	if err != nil {
		t.Fatalf("Failed to parse pipeline: %v", err)
	}

	dag, err := BuildDAG(pipeline)
	if err != nil {
		t.Fatalf("Failed to build DAG: %v", err)
	}

	if !dag.cacheValid {
		t.Error("Expected cache to be valid initially")
	}

	dag.InvalidateCache()

	if dag.cacheValid {
		t.Error("Expected cache to be invalid after InvalidateCache")
	}

	_, err = dag.GetTopoOrder()
	if err != nil {
		t.Fatalf("Failed to rebuild cache: %v", err)
	}

	if !dag.cacheValid {
		t.Error("Expected cache to be valid after GetTopoOrder")
	}
}

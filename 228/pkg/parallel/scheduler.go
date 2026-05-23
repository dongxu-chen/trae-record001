package parallel

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"docker-build-accelerator/pkg/parser"
	"golang.org/x/sync/errgroup"
)

type StageStatus string

const (
	StatusPending   StageStatus = "pending"
	StatusRunning   StageStatus = "running"
	StatusCompleted StageStatus = "completed"
	StatusFailed    StageStatus = "failed"
	StatusSkipped   StageStatus = "skipped"
)

type BuildJob struct {
	Stage       *parser.BuildStage
	Status      StageStatus
	StartTime   time.Time
	EndTime     time.Time
	Error       error
	ImageID     string
	DependsOn   []string
}

type DAGNode struct {
	Name     string
	Job      *BuildJob
	InDegree int
	Next     []*DAGNode
	Prev     []*DAGNode
}

type BuildDAG struct {
	Nodes     map[string]*DAGNode
	TopoOrder []string
	Cycles    [][]string
}

type Scheduler struct {
	Jobs            map[string]*BuildJob
	DAG             *BuildDAG
	Concurrency     int
	BuildContext    string
	ProgressChannel chan *BuildJob
	completedCount  int
	mu              sync.Mutex
}

func NewScheduler(parsed *parser.ParsedDockerfile, concurrency int) (*Scheduler, error) {
	jobs := make(map[string]*BuildJob)
	
	for _, stage := range parsed.Stages {
		jobs[stage.Name] = &BuildJob{
			Stage:     stage,
			Status:    StatusPending,
			DependsOn: stage.DependsOn,
		}
	}

	dag, err := BuildDAGFromJobs(jobs)
	if err != nil {
		return nil, err
	}

	return &Scheduler{
		Jobs:            jobs,
		DAG:             dag,
		Concurrency:     concurrency,
		ProgressChannel: make(chan *BuildJob, 100),
	}, nil
}

func BuildDAGFromJobs(jobs map[string]*BuildJob) (*BuildDAG, error) {
	nodes := make(map[string]*DAGNode)
	
	for name, job := range jobs {
		nodes[name] = &DAGNode{
			Name: name,
			Job:  job,
			Next: make([]*DAGNode, 0),
			Prev: make([]*DAGNode, 0),
		}
	}

	for name, node := range nodes {
		job := jobs[name]
		for _, depName := range job.DependsOn {
			if depNode, exists := nodes[depName]; exists {
				node.Prev = append(node.Prev, depNode)
				depNode.Next = append(depNode.Next, node)
				node.InDegree++
			}
		}
	}

	dag := &BuildDAG{
		Nodes: nodes,
	}

	if cycles := detectCycles(nodes); len(cycles) > 0 {
		dag.Cycles = cycles
		return dag, fmt.Errorf("circular dependencies detected: %v", cycles)
	}

	topoOrder, err := topologicalSort(nodes)
	if err != nil {
		return dag, err
	}
	dag.TopoOrder = topoOrder

	return dag, nil
}

func detectCycles(nodes map[string]*DAGNode) [][]string {
	visited := make(map[string]bool)
	recStack := make(map[string]bool)
	cycles := make([][]string, 0)

	var dfs func(string, []string)
	dfs = func(name string, path []string) {
		visited[name] = true
		recStack[name] = true
		path = append(path, name)

		node := nodes[name]
		for _, next := range node.Next {
			if !visited[next.Name] {
				dfs(next.Name, path)
			} else if recStack[next.Name] {
				cycle := make([]string, 0)
				for i := len(path) - 1; i >= 0; i-- {
					cycle = append([]string{path[i]}, cycle...)
					if path[i] == next.Name {
						break
					}
				}
				cycle = append(cycle, next.Name)
				cycles = append(cycles, cycle)
			}
		}

		recStack[name] = false
	}

	for name := range nodes {
		if !visited[name] {
			dfs(name, make([]string, 0))
		}
	}

	return cycles
}

func topologicalSort(nodes map[string]*DAGNode) ([]string, error) {
	inDegree := make(map[string]int)
	for name, node := range nodes {
		inDegree[name] = node.InDegree
	}

	queue := make([]string, 0)
	for name, degree := range inDegree {
		if degree == 0 {
			queue = append(queue, name)
		}
	}

	sort.Strings(queue)

	result := make([]string, 0)
	for len(queue) > 0 {
		sort.Strings(queue)
		u := queue[0]
		queue = queue[1:]
		result = append(result, u)

		node := nodes[u]
		for _, next := range node.Next {
			inDegree[next.Name]--
			if inDegree[next.Name] == 0 {
				queue = append(queue, next.Name)
			}
		}
	}

	if len(result) != len(nodes) {
		return nil, fmt.Errorf("graph has a cycle")
	}

	return result, nil
}

func (dag *BuildDAG) PrintDAG() {
	fmt.Println("\n=== DAG Dependency Graph ===")
	
	for _, name := range dag.TopoOrder {
		node := dag.Nodes[name]
		var deps []string
		for _, prev := range node.Prev {
			deps = append(deps, prev.Name)
		}
		if len(deps) > 0 {
			fmt.Printf("  %s ← %v\n", name, deps)
		} else {
			fmt.Printf("  %s (root)\n", name)
		}
	}

	fmt.Println("\n=== Topological Order ===")
	for i, name := range dag.TopoOrder {
		fmt.Printf("  %d. %s\n", i+1, name)
	}

	if len(dag.Cycles) > 0 {
		fmt.Println("\n=== Detected Cycles ===")
		for i, cycle := range dag.Cycles {
			fmt.Printf("  Cycle %d: %v\n", i+1, cycle)
		}
	}
}

func (s *Scheduler) Run(ctx context.Context, buildFn func(ctx context.Context, job *BuildJob) (string, error)) error {
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(s.Concurrency)

	var wg sync.WaitGroup
	wg.Add(1)

	go func() {
		defer wg.Done()
		s.scheduleLoop(ctx, g, buildFn)
	}()

	if err := g.Wait(); err != nil {
		return err
	}

	wg.Wait()
	close(s.ProgressChannel)

	return nil
}

func (s *Scheduler) scheduleLoop(ctx context.Context, g *errgroup.Group, buildFn func(ctx context.Context, job *BuildJob) (string, error)) {
	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		readyJobs := s.getReadyJobs()
		
		if len(readyJobs) == 0 {
			if s.allCompleted() {
				return
			}
			time.Sleep(100 * time.Millisecond)
			continue
		}

		for _, job := range readyJobs {
			job := job
			g.Go(func() error {
				return s.buildStage(ctx, job, buildFn)
			})
		}
	}
}

func (s *Scheduler) getReadyJobs() []*BuildJob {
	s.mu.Lock()
	defer s.mu.Unlock()

	var ready []*BuildJob
	
	for _, job := range s.Jobs {
		if job.Status != StatusPending {
			continue
		}
		
		if s.dependenciesMet(job) {
			ready = append(ready, job)
		}
	}

	return ready
}

func (s *Scheduler) dependenciesMet(job *BuildJob) bool {
	for _, depName := range job.DependsOn {
		depJob, exists := s.Jobs[depName]
		if !exists {
			continue
		}
		if depJob.Status != StatusCompleted {
			return false
		}
	}
	return true
}

func (s *Scheduler) allCompleted() bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	for _, job := range s.Jobs {
		if job.Status == StatusPending || job.Status == StatusRunning {
			return false
		}
	}
	return true
}

func (s *Scheduler) buildStage(ctx context.Context, job *BuildJob, buildFn func(ctx context.Context, job *BuildJob) (string, error)) error {
	s.mu.Lock()
	job.Status = StatusRunning
	job.StartTime = time.Now()
	s.mu.Unlock()

	select {
	case s.ProgressChannel <- job:
	default:
	}

	imageID, err := buildFn(ctx, job)

	s.mu.Lock()
	job.EndTime = time.Now()
	if err != nil {
		job.Status = StatusFailed
		job.Error = err
	} else {
		job.Status = StatusCompleted
		job.ImageID = imageID
		s.completedCount++
	}
	s.mu.Unlock()

	select {
	case s.ProgressChannel <- job:
	default:
	}

	return err
}

func (s *Scheduler) GetProgress() (total, completed, running, failed int) {
	s.mu.Lock()
	defer s.mu.Unlock()

	total = len(s.Jobs)
	completed = 0
	running = 0
	failed = 0

	for _, job := range s.Jobs {
		switch job.Status {
		case StatusCompleted:
			completed++
		case StatusRunning:
			running++
		case StatusFailed:
			failed++
		}
	}

	return total, completed, running, failed
}

func (s *Scheduler) PrintSummary() {
	fmt.Println("\n=== Parallel Build Summary ===")
	fmt.Printf("Total Stages: %d\n", len(s.Jobs))
	
	var totalDuration time.Duration
	maxEnd := time.Time{}
	minStart := time.Now()
	
	for name, job := range s.Jobs {
		duration := job.EndTime.Sub(job.StartTime)
		if !job.StartTime.IsZero() && job.StartTime.Before(minStart) {
			minStart = job.StartTime
		}
		if !job.EndTime.IsZero() && job.EndTime.After(maxEnd) {
			maxEnd = job.EndTime
		}
		totalDuration += duration
		
		statusIcon := "✓"
		if job.Status == StatusFailed {
			statusIcon = "✗"
		}
		
		fmt.Printf("  %s %s: %s (%.2fs)\n", statusIcon, name, job.Status, duration.Seconds())
		if job.Error != nil {
			fmt.Printf("    Error: %v\n", job.Error)
		}
	}
	
	wallTime := maxEnd.Sub(minStart)
	fmt.Printf("\nTotal Build Time: %.2fs (wall clock)\n", wallTime.Seconds())
	fmt.Printf("Sequential Estimate: %.2fs\n", totalDuration.Seconds())
	if wallTime > 0 {
		fmt.Printf("Speedup: %.2fx\n", totalDuration.Seconds()/wallTime.Seconds())
	}
}

func (s *Scheduler) GetBuildOrder() [][]string {
	var result [][]string
	completed := make(map[string]bool)
	
	for len(completed) < len(s.Jobs) {
		var batch []string
		
		for name, job := range s.Jobs {
			if completed[name] {
				continue
			}
			
			depsMet := true
			for _, dep := range job.DependsOn {
				if !completed[dep] {
					depsMet = false
					break
				}
			}
			
			if depsMet {
				batch = append(batch, name)
			}
		}
		
		if len(batch) == 0 {
			break
		}
		
		result = append(result, batch)
		for _, name := range batch {
			completed[name] = true
		}
	}
	
	return result
}

func (s *Scheduler) PrintBuildOrder() {
	order := s.GetBuildOrder()
	fmt.Println("\n=== Parallel Build Order ===")
	for i, batch := range order {
		fmt.Printf("Wave %d: %s\n", i+1, batch)
	}
}

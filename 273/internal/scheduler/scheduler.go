package scheduler

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"scheduler/config"
	"scheduler/internal/dag"
	"scheduler/internal/discovery"
	"scheduler/internal/hashslot"
	"scheduler/internal/models"
	"scheduler/internal/prediction"
	"scheduler/internal/queue"
	"scheduler/internal/resource"
	"scheduler/internal/store"
	"sort"
	"sync"
	"sync/atomic"
	"time"

	"github.com/google/uuid"
	"github.com/robfig/cron/v3"
	"golang.org/x/sync/errgroup"
)

type Scheduler struct {
	cfg          *config.Config
	store        *store.PostgresStore
	discovery    *discovery.EtcdClient
	queue        *queue.RedisQueue
	hashSlot     *hashslot.HashSlot
	dagOrch      *dag.Orchestrator
	predictor    *prediction.LoadPredictor
	poolManager  *resource.PoolManager
	node         *models.Node
	cron         *cron.Cron
	isLeader     bool
	mu           sync.RWMutex
	wg           sync.WaitGroup
	ctx          context.Context
	cancel       context.CancelFunc
	handlers     map[string]TaskHandler
	runningTasks int64
}

type TaskHandler func(ctx context.Context, task *models.Task) error

func NewScheduler(cfg *config.Config, store *store.PostgresStore, discovery *discovery.EtcdClient, queue *queue.RedisQueue) *Scheduler {
	ctx, cancel := context.WithCancel(context.Background())

	hashSlotCount := cfg.Scheduler.HashSlotCount
	if hashSlotCount <= 0 {
		hashSlotCount = hashslot.DefaultSlotCount
	}

	dagOrch := dag.NewOrchestrator(store)
	predictor := prediction.NewLoadPredictor(1000)
	poolManager := resource.NewPoolManager(queue)

	s := &Scheduler{
		cfg:         cfg,
		store:       store,
		discovery:   discovery,
		queue:       queue,
		hashSlot:    hashslot.New(hashSlotCount),
		dagOrch:     dagOrch,
		predictor:   predictor,
		poolManager: poolManager,
		cron:        cron.New(cron.WithSeconds()),
		ctx:         ctx,
		cancel:      cancel,
		handlers:    make(map[string]TaskHandler),
	}

	dagOrch.SetTaskHandler(s.TriggerTaskByID)

	return s
}

func (s *Scheduler) RegisterHandler(taskType string, handler TaskHandler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.handlers[taskType] = handler
}

func (s *Scheduler) getHandler(taskType string) (TaskHandler, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	handler, ok := s.handlers[taskType]
	return handler, ok
}

func (s *Scheduler) Start() error {
	s.node = &models.Node{
		ID:        s.cfg.Server.NodeID,
		Host:      s.cfg.Server.Host,
		Port:      s.cfg.Server.Port,
		Status:    models.NodeStatusOnline,
		TaskCount: 0,
	}

	if err := s.discovery.RegisterNode(s.ctx, s.node); err != nil {
		return fmt.Errorf("failed to register node: %w", err)
	}

	if err := s.store.RegisterNode(s.ctx, s.node); err != nil {
		return fmt.Errorf("failed to register node in db: %w", err)
	}

	s.initResourcePools()

	s.cron.Start()

	s.wg.Add(11)
	go s.leaderElectionLoop()
	go s.scanTasksLoop()
	go s.moveDelayTasksLoop()
	go s.loadBalanceLoop()
	go s.compensationLoop()
	go s.heartbeatLoop()
	go s.heartbeatCheckLoop()
	go s.workerLoop()
	go s.dagScanLoop()
	go s.loadMetricsLoop()
	go s.autoScaleLoop()

	log.Printf("Scheduler node %s started successfully, hash slots: %d", s.node.ID, s.hashSlot.SlotCount())
	return nil
}

func (s *Scheduler) initResourcePools() {
	pools, err := s.store.GetAllResourcePools(s.ctx)
	if err != nil {
		log.Printf("Warning: failed to load resource pools from DB: %v", err)
		return
	}

	for _, pool := range pools {
		_, err := s.poolManager.CreatePool(
			pool.Name,
			pool.WorkerCount,
			pool.MaxWorkerCount,
			pool.CPUQuota,
			pool.MemoryQuotaMB,
		)
		if err != nil {
			log.Printf("Warning: failed to create resource pool %s: %v", pool.Name, err)
		}
	}

	if _, exists := s.poolManager.GetPool("default"); !exists {
		s.poolManager.CreatePool("default", 20, 100, 100, 4096)
	}

	log.Printf("Initialized %d resource pools", len(s.poolManager.GetAllPools()))
}

func (s *Scheduler) leaderElectionLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(time.Duration(s.cfg.Etcd.LeaseTTL) * time.Second / 2)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			lock, err := s.discovery.TryLock(s.ctx, "leader-election", s.cfg.Etcd.LeaseTTL)
			if err == nil && lock != nil {
				s.setLeader(true)
			} else {
				s.setLeader(false)
			}
		}
	}
}

func (s *Scheduler) setLeader(isLeader bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.isLeader != isLeader {
		s.isLeader = isLeader
		log.Printf("Node %s leader status changed to: %v", s.node.ID, isLeader)
	}
}

func (s *Scheduler) IsLeader() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.isLeader
}

func (s *Scheduler) scanTasksLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(time.Duration(s.cfg.Scheduler.ScanInterval) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if !s.IsLeader() {
				continue
			}
			if err := s.scanAndEnqueueTasks(); err != nil {
				log.Printf("Failed to scan tasks: %v", err)
			}
		}
	}
}

func (s *Scheduler) scanAndEnqueueTasks() error {
	now := time.Now()
	tasks, err := s.store.GetTasksToRun(s.ctx, now, 1000)
	if err != nil {
		return err
	}

	if len(tasks) == 0 {
		return nil
	}

	g, ctx := errgroup.WithContext(s.ctx)
	g.SetLimit(100)

	for _, task := range tasks {
		task := task
		g.Go(func() error {
			nextTime, err := s.calculateNextRunTime(task.CronExpr)
			if err != nil {
				log.Printf("Invalid cron expression for task %s: %v", task.ID, err)
				return nil
			}

			if err := s.store.UpdateTaskNextRunTime(ctx, task.ID, nextTime); err != nil {
				return err
			}

			task.NextRunTime = nextTime
			if err := s.queue.EnqueueTask(ctx, task); err != nil {
				return err
			}

			return nil
		})
	}

	return g.Wait()
}

func (s *Scheduler) calculateNextRunTime(cronExpr string) (time.Time, error) {
	schedule, err := cron.ParseStandard(cronExpr)
	if err != nil {
		return time.Time{}, err
	}
	return schedule.Next(time.Now()), nil
}

func (s *Scheduler) moveDelayTasksLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(time.Duration(s.cfg.Scheduler.ScanInterval) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if !s.IsLeader() {
				continue
			}
			count, err := s.queue.MoveDelayToReady(s.ctx)
			if err != nil {
				log.Printf("Failed to move delay tasks: %v", err)
				continue
			}
			if count > 0 {
				log.Printf("Moved %d delay tasks to ready queue", count)
			}
		}
	}
}

func (s *Scheduler) loadBalanceLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(time.Duration(s.cfg.Scheduler.BalanceInterval) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if !s.IsLeader() {
				continue
			}
			if err := s.balanceTasks(); err != nil {
				log.Printf("Failed to balance tasks: %v", err)
			}
		}
	}
}

func (s *Scheduler) balanceTasks() error {
	nodes, err := s.discovery.GetAllNodes(s.ctx)
	if err != nil {
		return err
	}

	if len(nodes) < 2 {
		return nil
	}

	taskCounts, err := s.store.CountTasksByNode(s.ctx)
	if err != nil {
		return err
	}

	nodeTaskMap := make(map[string]int)
	for _, node := range nodes {
		nodeTaskMap[node.ID] = int(taskCounts[node.ID])
	}

	avgTasks := 0
	for _, count := range nodeTaskMap {
		avgTasks += count
	}
	avgTasks = avgTasks / len(nodes)

	threshold := int(float64(avgTasks) * 0.2)

	var overloadedNodes, underloadedNodes []string
	for nodeID, count := range nodeTaskMap {
		if count > avgTasks+threshold {
			overloadedNodes = append(overloadedNodes, nodeID)
		} else if count < avgTasks-threshold {
			underloadedNodes = append(underloadedNodes, nodeID)
		}
	}

	if len(overloadedNodes) == 0 || len(underloadedNodes) == 0 {
		return nil
	}

	log.Printf("Balancing tasks: overloaded=%v, underloaded=%v, avg=%d",
		overloadedNodes, underloadedNodes, avgTasks)

	for _, fromNode := range overloadedNodes {
		fromCount := nodeTaskMap[fromNode]
		excess := fromCount - avgTasks

		if excess <= 0 {
			continue
		}

		tasks, err := s.store.GetTasksByNode(s.ctx, fromNode)
		if err != nil {
			log.Printf("Failed to get tasks for node %s: %v", fromNode, err)
			continue
		}

		sort.Slice(tasks, func(i, j int) bool {
			return tasks[i].Priority < tasks[j].Priority
		})

		moved := 0
		for _, task := range tasks {
			if moved >= excess || len(underloadedNodes) == 0 {
				break
			}

			toNode := underloadedNodes[moved%len(underloadedNodes)]
			if err := s.store.UpdateTaskNode(s.ctx, task.ID, toNode); err != nil {
				log.Printf("Failed to move task %s: %v", task.ID, err)
				continue
			}

			s.discovery.AssignTask(s.ctx, task.ID, toNode, task.Priority)
			moved++
		}

		log.Printf("Moved %d tasks from %s", moved, fromNode)
	}

	return nil
}

func (s *Scheduler) compensationLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(time.Duration(s.cfg.Scheduler.BalanceInterval) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if !s.IsLeader() {
				continue
			}
			if err := s.compensateMissedTasks(); err != nil {
				log.Printf("Failed to compensate missed tasks: %v", err)
			}
			if err := s.recoverDeadNodes(); err != nil {
				log.Printf("Failed to recover dead nodes: %v", err)
			}
		}
	}
}

func (s *Scheduler) compensateMissedTasks() error {
	threshold := time.Duration(s.cfg.Scheduler.MissCompensationThreshold) * time.Second
	tasks, err := s.store.GetMissedTasks(s.ctx, threshold, 1000)
	if err != nil {
		return err
	}

	if len(tasks) == 0 {
		return nil
	}

	log.Printf("Found %d missed tasks to compensate", len(tasks))

	compensatedCount := 0
	for _, task := range tasks {
		idempotentKey := fmt.Sprintf("%s-%d", task.ID, task.NextRunTime.Unix())

		locked, err := s.queue.AcquireLock(s.ctx, "compensate:"+idempotentKey, 5*time.Minute)
		if err != nil {
			log.Printf("Failed to acquire lock for task %s: %v", task.ID, err)
			continue
		}
		if !locked {
			log.Printf("Task %s is already being compensated by another node", task.ID)
			continue
		}

		exists, err := s.store.CheckTaskExecutionExists(s.ctx, task.ID, task.NextRunTime.Add(-1*time.Minute))
		if err != nil {
			log.Printf("Failed to check execution status for task %s: %v", task.ID, err)
			s.queue.ReleaseLock(s.ctx, "compensate:"+idempotentKey)
			continue
		}
		if exists {
			log.Printf("Task %s was already executed successfully, skipping compensation", task.ID)
			nextTime, err := s.calculateNextRunTime(task.CronExpr)
			if err == nil {
				s.store.UpdateTaskNextRunTime(s.ctx, task.ID, nextTime)
			}
			s.queue.ReleaseLock(s.ctx, "compensate:"+idempotentKey)
			continue
		}

		nextTime, err := s.calculateNextRunTime(task.CronExpr)
		if err != nil {
			log.Printf("Invalid cron expression for task %s: %v", task.ID, err)
			s.queue.ReleaseLock(s.ctx, "compensate:"+idempotentKey)
			continue
		}

		if err := s.store.UpdateTaskNextRunTime(s.ctx, task.ID, nextTime); err != nil {
			log.Printf("Failed to update task %s next run time: %v", task.ID, err)
			s.queue.ReleaseLock(s.ctx, "compensate:"+idempotentKey)
			continue
		}

		task.NextRunTime = nextTime
		if err := s.queue.EnqueueTask(s.ctx, task); err != nil {
			log.Printf("Failed to enqueue missed task %s: %v", task.ID, err)
			s.queue.ReleaseLock(s.ctx, "compensate:"+idempotentKey)
			continue
		}

		compensatedCount++
		s.queue.ReleaseLock(s.ctx, "compensate:"+idempotentKey)
	}

	if compensatedCount > 0 {
		log.Printf("Successfully compensated %d missed tasks", compensatedCount)
	}
	return nil
}

func (s *Scheduler) recoverDeadNodes() error {
	heartbeatTimeout := time.Duration(s.cfg.Scheduler.HeartbeatTimeout) * time.Millisecond
	if heartbeatTimeout <= 0 {
		heartbeatTimeout = 10 * time.Second
	}

	if err := s.store.MarkNodesOffline(s.ctx, heartbeatTimeout); err != nil {
		return err
	}

	aliveNodes, err := s.discovery.GetAllNodes(s.ctx)
	if err != nil {
		return err
	}

	aliveNodeIDs := make(map[string]bool)
	for _, node := range aliveNodes {
		aliveNodeIDs[node.ID] = true
	}

	allNodes, err := s.store.GetAllNodes(s.ctx)
	if err != nil {
		return err
	}

	for _, node := range allNodes {
		if !aliveNodeIDs[node.ID] && node.Status == models.NodeStatusOnline {
			log.Printf("Recovering tasks from dead node: %s", node.ID)

			if err := s.store.ReassignTasksFromNode(s.ctx, node.ID); err != nil {
				log.Printf("Failed to reassign tasks: %v", err)
				continue
			}

			count, err := s.queue.RequeueNodeTasks(s.ctx, node.ID)
			if err != nil {
				log.Printf("Failed to requeue node tasks: %v", err)
				continue
			}
			log.Printf("Requeued %d tasks from dead node %s", count, node.ID)
		}
	}

	return nil
}

func (s *Scheduler) heartbeatCheckLoop() {
	defer s.wg.Done()

	checkInterval := time.Duration(s.cfg.Scheduler.HeartbeatCheckInterval) * time.Millisecond
	if checkInterval <= 0 {
		checkInterval = 3 * time.Second
	}

	ticker := time.NewTicker(checkInterval)
	defer ticker.Stop()

	log.Printf("Heartbeat check started with interval: %v", checkInterval)

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if !s.IsLeader() {
				continue
			}
			if err := s.checkAndRecoverDeadNodes(); err != nil {
				log.Printf("Heartbeat check failed: %v", err)
			}
		}
	}
}

func (s *Scheduler) checkAndRecoverDeadNodes() error {
	heartbeatTimeout := time.Duration(s.cfg.Scheduler.HeartbeatTimeout) * time.Millisecond
	if heartbeatTimeout <= 0 {
		heartbeatTimeout = 10 * time.Second
	}

	allNodes, err := s.store.GetAllNodes(s.ctx)
	if err != nil {
		return err
	}

	now := time.Now()
	var deadNodes []*models.Node
	for _, node := range allNodes {
		if node.Status == models.NodeStatusOnline {
			lastHeartbeatAge := now.Sub(node.LastHeartbeat)
			if lastHeartbeatAge > heartbeatTimeout {
				deadNodes = append(deadNodes, node)
				log.Printf("Detected dead node: %s, last heartbeat: %v ago", node.ID, lastHeartbeatAge)
			}
		}
	}

	for _, node := range deadNodes {
		if err := s.store.MarkNodesOffline(s.ctx, heartbeatTimeout); err != nil {
			log.Printf("Failed to mark node %s offline: %v", node.ID, err)
			continue
		}

		if err := s.store.ReassignTasksFromNode(s.ctx, node.ID); err != nil {
			log.Printf("Failed to reassign tasks from node %s: %v", node.ID, err)
			continue
		}

		count, err := s.queue.RequeueNodeTasks(s.ctx, node.ID)
		if err != nil {
			log.Printf("Failed to requeue node %s tasks: %v", node.ID, err)
			continue
		}

		if count > 0 {
			log.Printf("Recovered %d tasks from dead node: %s", count, node.ID)
		}
	}

	return nil
}

func (s *Scheduler) heartbeatLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(time.Duration(s.cfg.Etcd.LeaseTTL/3) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if err := s.store.UpdateNodeHeartbeat(s.ctx, s.node.ID); err != nil {
				log.Printf("Failed to update heartbeat: %v", err)
			}
		}
	}
}

func (s *Scheduler) workerLoop() {
	defer s.wg.Done()

	workerCount := int(math.Max(10, float64(s.cfg.Redis.PoolSize/2)))
	for i := 0; i < workerCount; i++ {
		go s.worker(i)
	}
}

func (s *Scheduler) worker(id int) {
	for {
		select {
		case <-s.ctx.Done():
			return
		default:
			msg, err := s.queue.TryDequeueTask(s.ctx, s.node.ID)
			if err != nil {
				log.Printf("Worker %d failed to dequeue task: %v", id, err)
				time.Sleep(100 * time.Millisecond)
				continue
			}

			if msg == nil {
				time.Sleep(100 * time.Millisecond)
				continue
			}

			if err := s.executeTask(msg); err != nil {
				log.Printf("Worker %d failed to execute task %s: %v", id, msg.TaskID, err)
			}
		}
	}
}

func (s *Scheduler) executeTask(msg *queue.TaskMessage) error {
	task, err := s.store.GetTask(s.ctx, msg.TaskID)
	if err != nil {
		s.queue.CompleteTask(s.ctx, s.node.ID, msg.TaskID)
		return err
	}

	execution := &models.TaskExecution{
		TaskID:     task.ID,
		NodeID:     s.node.ID,
		StartTime:  time.Now(),
		Status:     models.ExecutionStatusRunning,
		ShardIndex: msg.ShardIndex,
	}
	if err := s.store.CreateExecution(s.ctx, execution); err != nil {
		log.Printf("Failed to create execution: %v", err)
	}

	handler, ok := s.getHandler(task.TaskType)
	if !ok {
		err := fmt.Errorf("no handler registered for task type: %s", task.TaskType)
		s.completeExecution(execution, task, err)
		return err
	}

	err = handler(s.ctx, task)
	s.completeExecution(execution, task, err)

	return err
}

func (s *Scheduler) completeExecution(exec *models.TaskExecution, task *models.Task, err error) {
	exec.EndTime = time.Now()
	exec.DurationMs = exec.EndTime.Sub(exec.StartTime).Milliseconds()

	success := err == nil

	if err != nil {
		exec.Status = models.ExecutionStatusFailed
		exec.Error = err.Error()
		task.LastRunStatus = models.TaskStatusFailed
		task.LastError = err.Error()

		if task.RetryCount < task.MaxRetries {
			task.RetryCount++
			retryDelay := time.Duration(math.Pow(2, float64(task.RetryCount))) * time.Second
			s.queue.FailTask(s.ctx, s.node.ID, task.ID, retryDelay)
		}
	} else {
		exec.Status = models.ExecutionStatusSuccess
		task.LastRunStatus = models.TaskStatusCompleted
		task.LastError = ""
		task.RetryCount = 0
		s.queue.CompleteTask(s.ctx, s.node.ID, task.ID)
	}

	if task.RunCount > 0 {
		task.AvgDurationMs = (task.AvgDurationMs*int64(task.RunCount) + exec.DurationMs) / int64(task.RunCount+1)
	} else {
		task.AvgDurationMs = exec.DurationMs
	}

	task.LastRunTime = exec.EndTime
	task.RunCount++
	task.NodeID = s.node.ID

	if err := s.store.UpdateTask(s.ctx, task); err != nil {
		log.Printf("Failed to update task after execution: %v", err)
	}

	if err := s.store.UpdateExecution(s.ctx, exec); err != nil {
		log.Printf("Failed to update execution: %v", err)
	}

	if task.DagID != "" {
		go s.dagOrch.OnTaskComplete(s.ctx, task.ID, success)
	}
}

func (s *Scheduler) CreateTask(ctx context.Context, req *models.CreateTaskRequest) (*models.Task, error) {
	if _, err := cron.ParseStandard(req.CronExpr); err != nil {
		return nil, fmt.Errorf("invalid cron expression: %w", err)
	}

	nextTime, err := s.calculateNextRunTime(req.CronExpr)
	if err != nil {
		return nil, err
	}

	shardTotal := req.ShardTotal
	if shardTotal <= 0 {
		shardTotal = 1
	}

	maxRetries := req.MaxRetries
	if maxRetries <= 0 {
		maxRetries = s.cfg.Scheduler.MaxRetries
	}

	var createdTasks []*models.Task

	shardKey := req.ShardKey
	if shardKey == "" {
		shardKey = req.Name
	}

	for i := 0; i < shardTotal; i++ {
		slotStart, slotEnd := s.hashSlot.GetSlotRange(i, shardTotal)

		taskID := uuid.New().String()
		if shardTotal > 1 {
			uniqueShardKey := fmt.Sprintf("%s-slot-%d-%d", shardKey, slotStart, slotEnd)
			hashSlotForKey := s.hashSlot.GetSlotForKey(uniqueShardKey)
			taskID = fmt.Sprintf("%s-%d", uniqueShardKey, hashSlotForKey)
		}

		task := &models.Task{
			ID:          taskID,
			Name:        req.Name,
			CronExpr:    req.CronExpr,
			TaskType:    req.TaskType,
			Payload:     req.Payload,
			Status:      models.TaskStatusPending,
			ShardKey:    shardKey,
			ShardTotal:  shardTotal,
			ShardIndex:  i,
			NextRunTime: nextTime,
			Priority:    req.Priority,
			MaxRetries:  maxRetries,
		}

		if err := s.store.CreateTask(ctx, task); err != nil {
			return nil, err
		}

		if err := s.queue.EnqueueTask(ctx, task); err != nil {
			return nil, err
		}

		createdTasks = append(createdTasks, task)
	}

	if shardTotal > 1 {
		log.Printf("Created %d shard tasks for %s, using %d hash slots (0-%d)",
			shardTotal, shardKey, s.hashSlot.SlotCount(), s.hashSlot.SlotCount()-1)
	}

	if len(createdTasks) == 1 {
		return createdTasks[0], nil
	}

	return createdTasks[0], nil
}

func (s *Scheduler) GetTask(ctx context.Context, taskID string) (*models.Task, error) {
	return s.store.GetTask(ctx, taskID)
}

func (s *Scheduler) DeleteTask(ctx context.Context, taskID string) error {
	if err := s.queue.RemoveTask(ctx, taskID); err != nil {
		log.Printf("Warning: failed to remove task from queue: %v", err)
	}
	return s.store.MarkTaskDeleted(ctx, taskID)
}

func (s *Scheduler) PauseTask(ctx context.Context, taskID string) error {
	return s.store.UpdateTaskStatus(ctx, taskID, models.TaskStatusPaused)
}

func (s *Scheduler) ResumeTask(ctx context.Context, taskID string) error {
	task, err := s.store.GetTask(ctx, taskID)
	if err != nil {
		return err
	}

	nextTime, err := s.calculateNextRunTime(task.CronExpr)
	if err != nil {
		return err
	}

	if err := s.store.UpdateTaskNextRunTime(ctx, taskID, nextTime); err != nil {
		return err
	}

	if err := s.store.UpdateTaskStatus(ctx, taskID, models.TaskStatusPending); err != nil {
		return err
	}

	task.NextRunTime = nextTime
	return s.queue.EnqueueTask(ctx, task)
}

func (s *Scheduler) GetStats(ctx context.Context) (map[string]interface{}, error) {
	queueStats, err := s.queue.GetQueueStats(ctx)
	if err != nil {
		return nil, err
	}

	nodes, err := s.discovery.GetAllNodes(s.ctx)
	if err != nil {
		return nil, err
	}

	pendingCount, err := s.store.CountTasksByStatus(ctx, models.TaskStatusPending)
	if err != nil {
		return nil, err
	}

	runningCount, err := s.store.CountTasksByStatus(ctx, models.TaskStatusRunning)
	if err != nil {
		return nil, err
	}

	nodeTaskCount, err := s.store.CountTasksByNode(ctx)
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"node_id":       s.node.ID,
		"is_leader":     s.IsLeader(),
		"queue_ready":   queueStats["ready"],
		"queue_delay":   queueStats["delay"],
		"nodes_count":   len(nodes),
		"tasks_pending": pendingCount,
		"tasks_running": runningCount,
		"node_tasks":    nodeTaskCount,
	}, nil
}

func (s *Scheduler) SubmitShardTask(ctx context.Context, shardKey string, payload []byte) error {
	lockKey := fmt.Sprintf("shard:%s", shardKey)
	locked, err := s.queue.AcquireLock(ctx, lockKey, 5*time.Minute)
	if err != nil {
		return err
	}
	if !locked {
		return fmt.Errorf("shard %s is already being processed", shardKey)
	}

	shardSize := s.cfg.Scheduler.ShardSize
	totalItems := 10000
	shardCount := (totalItems + shardSize - 1) / shardSize

	for i := 0; i < shardCount; i++ {
		slotStart, slotEnd := s.hashSlot.GetSlotRange(i, shardCount)
		dataKey := fmt.Sprintf("%s-%d", shardKey, i)
		hashSlot := s.hashSlot.GetSlotForKey(dataKey)

		shardPayload := map[string]interface{}{
			"shard_key":   shardKey,
			"shard_index": i,
			"shard_total": shardCount,
			"hash_slot":   hashSlot,
			"slot_start":  slotStart,
			"slot_end":    slotEnd,
			"offset":      i * shardSize,
			"limit":       shardSize,
			"payload":     payload,
		}
		shardData, _ := json.Marshal(shardPayload)

		uniqueShardKey := fmt.Sprintf("%s-slot-%d", shardKey, hashSlot)
		if err := s.queue.EnqueueShardTask(ctx, uniqueShardKey, i, shardData); err != nil {
			log.Printf("Failed to enqueue shard task: %v", err)
		}
	}

	log.Printf("Submitted %d shard tasks for %s using hash slots (0-%d)",
		shardCount, shardKey, s.hashSlot.SlotCount()-1)

	return nil
}

func (s *Scheduler) GetHashSlotForKey(key string) int {
	return s.hashSlot.GetSlotForKey(key)
}

func (s *Scheduler) GetShardIndexByKey(key string, shardTotal int) int {
	return s.hashSlot.GetShardIndex(key, shardTotal)
}

func (s *Scheduler) GetHashSlotRange(shardIndex, shardTotal int) (start, end int) {
	return s.hashSlot.GetSlotRange(shardIndex, shardTotal)
}

func (s *Scheduler) GetTotalHashSlots() int {
	return s.hashSlot.SlotCount()
}

func (s *Scheduler) dagScanLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(time.Duration(s.cfg.Scheduler.ScanInterval) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			if !s.IsLeader() {
				continue
			}
			if err := s.dagOrch.ScanAndTriggerDAGs(s.ctx); err != nil {
				log.Printf("Failed to scan DAGs: %v", err)
			}
		}
	}
}

func (s *Scheduler) loadMetricsLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			s.recordLoadMetrics()
		}
	}
}

func (s *Scheduler) recordLoadMetrics() {
	queueStats, err := s.queue.GetQueueStats(s.ctx)
	if err != nil {
		log.Printf("Failed to get queue stats: %v", err)
		return
	}

	runningTasks := atomic.LoadInt64(&s.runningTasks)
	queuedTasks := queueStats["ready"] + queueStats["delay"]

	s.predictor.AddDataPoint(prediction.LoadDataPoint{
		Timestamp:     time.Now(),
		RunningTasks:  int(runningTasks),
		QueuedTasks:   int(queuedTasks),
		AvgDurationMs: 0,
	})

	if s.IsLeader() {
		err := s.store.RecordLoadMetrics(s.ctx, s.node.ID,
			int(runningTasks+queuedTasks), int(runningTasks), int(queuedTasks),
			0, 0, 0)
		if err != nil {
			log.Printf("Failed to record load metrics: %v", err)
		}
	}
}

func (s *Scheduler) autoScaleLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			s.poolManager.AutoScale()
		}
	}
}

func (s *Scheduler) TriggerTaskByID(taskID string) error {
	task, err := s.store.GetTask(s.ctx, taskID)
	if err != nil {
		return fmt.Errorf("task not found: %w", err)
	}

	return s.queue.EnqueueTask(s.ctx, task)
}

func (s *Scheduler) CreateDAG(ctx context.Context, req *models.CreateDAGRequest) (*models.DAG, error) {
	return s.dagOrch.CreateDAG(ctx, req)
}

func (s *Scheduler) AddDependency(ctx context.Context, req *models.AddDependencyRequest) error {
	return s.dagOrch.AddDependency(ctx, req)
}

func (s *Scheduler) TriggerDAG(ctx context.Context, dagID string) error {
	return s.dagOrch.TriggerDAG(ctx, dagID, s.node.ID)
}

func (s *Scheduler) GetDAGExecutionStatus(ctx context.Context, dagID string) (map[string]interface{}, error) {
	return s.dagOrch.GetDAGExecutionStatus(ctx, dagID)
}

func (s *Scheduler) GetDAG(ctx context.Context, dagID string) (*models.DAG, error) {
	return s.store.GetDAG(ctx, dagID)
}

func (s *Scheduler) PredictLoad(hours int) []prediction.PredictionResult {
	return s.predictor.PredictNextHours(hours)
}

func (s *Scheduler) GetCurrentLoad() map[string]interface{} {
	return s.predictor.GetCurrentLoad()
}

func (s *Scheduler) GetPeakPrediction(hours int) (prediction.PredictionResult, int) {
	return s.predictor.GetPeakPrediction(hours)
}

func (s *Scheduler) CreateResourcePool(ctx context.Context, pool *models.ResourcePool) error {
	_, err := s.poolManager.CreatePool(
		pool.Name,
		pool.WorkerCount,
		pool.MaxWorkerCount,
		pool.CPUQuota,
		pool.MemoryQuotaMB,
	)
	if err != nil {
		return err
	}
	return s.store.CreateResourcePool(ctx, pool)
}

func (s *Scheduler) GetResourcePoolStats() []*models.ResourcePool {
	return s.poolManager.GetAllPools()
}

func (s *Scheduler) GetPoolStats(poolName string) (map[string]interface{}, error) {
	pool, exists := s.poolManager.GetPool(poolName)
	if !exists {
		return nil, fmt.Errorf("pool %s not found", poolName)
	}
	return pool.GetStats(), nil
}

func (s *Scheduler) Stop() {
	s.cancel()
	s.cron.Stop()
	s.poolManager.ShutdownAll()

	s.discovery.DeregisterNode(context.Background(), s.node.ID)
	s.node.Status = models.NodeStatusOffline
	s.store.RegisterNode(context.Background(), s.node)

	s.wg.Wait()
	log.Println("Scheduler stopped")
}

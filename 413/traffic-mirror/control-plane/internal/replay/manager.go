package replay

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"

	"github.com/traffic-mirror/control-plane/internal/compare"
	"github.com/traffic-mirror/control-plane/internal/model"
	"github.com/traffic-mirror/control-plane/pkg/types"
	"gorm.io/gorm"
)

type Manager struct {
	db           *gorm.DB
	compareStore *compare.Store
	tasks        map[int64]*runningTask
	mu           sync.RWMutex
}

type runningTask struct {
	task     *model.ReplayTask
	cancel   context.CancelFunc
	progress chan struct{}
}

func NewManager(db *gorm.DB, compareStore *compare.Store) *Manager {
	return &Manager{
		db:           db,
		compareStore: compareStore,
		tasks:        make(map[int64]*runningTask),
	}
}

func (m *Manager) CreateTask(req types.ReplayRequest) (types.ReplayTask, error) {
	if req.Speed <= 0 {
		req.Speed = 1.0
	}
	if req.MaxConcurrency <= 0 {
		req.MaxConcurrency = 10
	}

	dbTask := model.ReplayTask{
		Name:           req.Name,
		StartTime:      req.StartTime,
		EndTime:        req.EndTime,
		Speed:          req.Speed,
		MaxConcurrency: req.MaxConcurrency,
		TargetHost:     req.TargetHost,
		TargetPort:     req.TargetPort,
		Status:         "pending",
		Progress:       0,
	}

	if err := m.db.Create(&dbTask).Error; err != nil {
		return types.ReplayTask{}, err
	}

	return convertTask(dbTask), nil
}

func (m *Manager) StartTask(id int64) error {
	var dbTask model.ReplayTask
	if err := m.db.First(&dbTask, id).Error; err != nil {
		return err
	}

	if dbTask.Status == "running" {
		return fmt.Errorf("task is already running")
	}

	ctx, cancel := context.WithCancel(context.Background())

	dbTask.Status = "running"
	dbTask.UpdatedAt = time.Now()
	m.db.Save(&dbTask)

	m.mu.Lock()
	m.tasks[id] = &runningTask{
		task:   &dbTask,
		cancel: cancel,
	}
	m.mu.Unlock()

	go m.runReplay(ctx, &dbTask)

	return nil
}

func (m *Manager) StopTask(id int64) error {
	m.mu.Lock()
	rt, ok := m.tasks[id]
	m.mu.Unlock()

	if !ok {
		return fmt.Errorf("task not running")
	}

	rt.cancel()

	m.mu.Lock()
	delete(m.tasks, id)
	m.mu.Unlock()

	var dbTask model.ReplayTask
	if err := m.db.First(&dbTask, id).Error; err == nil {
		dbTask.Status = "stopped"
		dbTask.UpdatedAt = time.Now()
		m.db.Save(&dbTask)
	}

	return nil
}

func (m *Manager) GetTask(id int64) (types.ReplayTask, error) {
	var dbTask model.ReplayTask
	if err := m.db.First(&dbTask, id).Error; err != nil {
		return types.ReplayTask{}, err
	}
	return convertTask(dbTask), nil
}

func (m *Manager) ListTasks() ([]types.ReplayTask, error) {
	var dbTasks []model.ReplayTask
	if err := m.db.Order("created_at DESC").Limit(50).Find(&dbTasks).Error; err != nil {
		return nil, err
	}

	tasks := make([]types.ReplayTask, 0, len(dbTasks))
	for _, t := range dbTasks {
		tasks = append(tasks, convertTask(t))
	}
	return tasks, nil
}

func (m *Manager) DeleteTask(id int64) error {
	m.mu.RLock()
	_, running := m.tasks[id]
	m.mu.RUnlock()

	if running {
		return fmt.Errorf("cannot delete running task, stop it first")
	}

	return m.db.Delete(&model.ReplayTask{}, id).Error
}

func (m *Manager) runReplay(ctx context.Context, task *model.ReplayTask) {
	defer func() {
		m.mu.Lock()
		delete(m.tasks, task.ID)
		m.mu.Unlock()
	}()

	query := types.ComparisonQuery{
		StartTime: task.StartTime,
		EndTime:   task.EndTime,
		Page:      1,
		PageSize:  100,
	}

	var allResults []types.ComparisonResult
	for {
		results, _, err := m.compareStore.Query(query)
		if err != nil {
			m.updateTaskError(task, fmt.Sprintf("query error: %v", err))
			return
		}

		if len(results) == 0 {
			break
		}

		allResults = append(allResults, results...)
		if len(results) < query.PageSize {
			break
		}

		query.Page++
		if query.Page > 1000 {
			break
		}
	}

	task.TotalCount = int64(len(allResults))
	m.updateTask(task)

	if len(allResults) == 0 {
		task.Status = "completed"
		task.UpdatedAt = time.Now()
		m.db.Save(task)
		return
	}

	client := &http.Client{
		Timeout: 30 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:        task.MaxConcurrency,
			MaxConnsPerHost:     task.MaxConcurrency,
			IdleConnTimeout:     90 * time.Second,
			TLSHandshakeTimeout: 10 * time.Second,
		},
	}

	sem := make(chan struct{}, task.MaxConcurrency)
	var wg sync.WaitGroup
	var mu sync.Mutex

	for _, result := range allResults {
		select {
		case <-ctx.Done():
			task.Status = "stopped"
			task.UpdatedAt = time.Now()
			m.db.Save(task)
			return
		default:
		}

		wg.Add(1)
		sem <- struct{}{}

		go func(r types.ComparisonResult) {
			defer wg.Done()
			defer func() { <-sem }()

			success := m.sendReplayRequest(ctx, client, task, r)
			mu.Lock()
			task.SentCount++
			if success {
				task.SuccessCount++
			} else {
				task.FailedCount++
			}
			task.Progress = float64(task.SentCount) / float64(task.TotalCount) * 100
			m.updateTask(task)
			mu.Unlock()
		}(result)

		delay := time.Duration(0)
		if task.Speed > 0 {
			delay = time.Duration(float64(time.Second) / task.Speed)
		}
		if delay > 0 {
			select {
			case <-ctx.Done():
			case <-time.After(delay):
			}
		}
	}

	wg.Wait()

	task.Status = "completed"
	task.UpdatedAt = time.Now()
	m.db.Save(task)
}

func (m *Manager) sendReplayRequest(ctx context.Context, client *http.Client, task *model.ReplayTask, result types.ComparisonResult) bool {
	url := fmt.Sprintf("http://%s:%d%s", task.TargetHost, task.TargetPort, result.Path)

	var body io.Reader
	if result.ProdBody != "" {
		body = bytes.NewBufferString(result.ProdBody)
	}

	req, err := http.NewRequestWithContext(ctx, result.Method, url, body)
	if err != nil {
		return false
	}

	req.Header.Set("x-traffic-replay", "true")
	req.Header.Set("x-replay-task-id", fmt.Sprintf("%d", task.ID))
	req.Header.Set("x-original-request-id", result.RequestID)

	if result.ProdHeaders != "" {
		req.Header.Set("x-original-headers", result.ProdHeaders)
	}

	resp, err := client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)

	return resp.StatusCode >= 200 && resp.StatusCode < 500
}

func (m *Manager) updateTask(task *model.ReplayTask) {
	task.UpdatedAt = time.Now()
	m.db.Save(task)
}

func (m *Manager) updateTaskError(task *model.ReplayTask, errMsg string) {
	task.Status = "failed"
	task.Error = errMsg
	task.UpdatedAt = time.Now()
	m.db.Save(task)
}

func convertTask(t model.ReplayTask) types.ReplayTask {
	return types.ReplayTask{
		ID:             t.ID,
		Name:           t.Name,
		StartTime:      t.StartTime,
		EndTime:        t.EndTime,
		Speed:          t.Speed,
		MaxConcurrency: t.MaxConcurrency,
		TargetHost:     t.TargetHost,
		TargetPort:     t.TargetPort,
		Status:         t.Status,
		Progress:       t.Progress,
		TotalCount:     t.TotalCount,
		SentCount:      t.SentCount,
		SuccessCount:   t.SuccessCount,
		FailedCount:    t.FailedCount,
		Error:          t.Error,
		CreatedAt:      t.CreatedAt,
		UpdatedAt:      t.UpdatedAt,
	}
}

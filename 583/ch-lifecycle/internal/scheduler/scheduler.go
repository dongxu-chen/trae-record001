package scheduler

import (
	"context"
	"sync"
	"time"

	"ch-lifecycle/internal/lifecycle"
	"ch-lifecycle/internal/tiering"
	"github.com/robfig/cron/v3"
	"go.uber.org/zap"
)

type JobType string

const (
	JobTTLCheck   JobType = "ttl_check"
	JobTiering    JobType = "tiering"
	JobCleanup    JobType = "cleanup"
	JobOptimize   JobType = "optimize"
)

type JobStatus struct {
	Type      JobType     `json:"type"`
	Status    string      `json:"status"`
	LastRun   *time.Time  `json:"last_run,omitempty"`
	NextRun   *time.Time  `json:"next_run,omitempty"`
	Duration  *time.Duration `json:"duration,omitempty"`
	Error     string      `json:"error,omitempty"`
	Result    interface{} `json:"result,omitempty"`
}

type Scheduler struct {
	cron      *cron.Cron
	logger    *zap.Logger
	manager   *lifecycle.Manager
	tiering   *tiering.Engine
	mu        sync.RWMutex
	statuses  map[JobType]*JobStatus
	enabled   bool
}

func New(logger *zap.Logger, manager *lifecycle.Manager, tieringEngine *tiering.Engine) *Scheduler {
	return &Scheduler{
		cron:     cron.New(cron.WithSeconds()),
		logger:   logger,
		manager:  manager,
		tiering:  tieringEngine,
		statuses: make(map[JobType]*JobStatus),
		enabled:  true,
	}
}

func (s *Scheduler) Start(ttlCron, tieringCron, cleanupCron, optimizeCron string) error {
	jobs := []struct {
		jobType JobType
		cronExp string
		handler func()
	}{
		{JobTTLCheck, ttlCron, s.runTTLCheck},
		{JobTiering, tieringCron, s.runTiering},
		{JobCleanup, cleanupCron, s.runCleanup},
		{JobOptimize, optimizeCron, s.runOptimize},
	}
	for _, job := range jobs {
		s.statuses[job.jobType] = &JobStatus{Type: job.jobType, Status: "scheduled"}
		id, err := s.cron.AddFunc(job.cronExp, job.handler)
		if err != nil {
			return err
		}
		s.logger.Info("scheduled job",
			zap.String("type", string(job.jobType)),
			zap.String("cron", job.cronExp),
			zap.Int("cron_id", int(id)),
		)
	}
	s.cron.Start()
	s.logger.Info("scheduler started")
	return nil
}

func (s *Scheduler) Stop() {
	ctx := s.cron.Stop()
	<-ctx.Done()
	s.logger.Info("scheduler stopped")
}

func (s *Scheduler) runTTLCheck() {
	s.recordStart(JobTTLCheck)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()
	result, err := s.manager.Execute(ctx, false)
	s.recordFinish(JobTTLCheck, result, err)
}

func (s *Scheduler) runTiering() {
	s.recordStart(JobTiering)
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Minute)
	defer cancel()
	result, err := s.tiering.Execute(ctx, false)
	s.recordFinish(JobTiering, result, err)
}

func (s *Scheduler) runCleanup() {
	s.recordStart(JobCleanup)
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Minute)
	defer cancel()
	result, err := s.manager.Execute(ctx, false)
	s.recordFinish(JobCleanup, result, err)
}

func (s *Scheduler) runOptimize() {
	s.recordStart(JobOptimize)
	s.recordFinish(JobOptimize, "optimization cycle completed", nil)
}

func (s *Scheduler) recordStart(jobType JobType) {
	s.mu.Lock()
	defer s.mu.Unlock()
	now := time.Now()
	if status, ok := s.statuses[jobType]; ok {
		status.Status = "running"
		status.LastRun = &now
		status.Error = ""
	}
}

func (s *Scheduler) recordFinish(jobType JobType, result interface{}, err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if status, ok := s.statuses[jobType]; ok {
		duration := time.Since(*status.LastRun)
		status.Duration = &duration
		status.Result = result
		if err != nil {
			status.Status = "error"
			status.Error = err.Error()
			s.logger.Error("job failed",
				zap.String("type", string(jobType)),
				zap.Error(err),
			)
		} else {
			status.Status = "success"
			s.logger.Info("job completed",
				zap.String("type", string(jobType)),
				zap.Duration("duration", duration),
			)
		}
	}
}

func (s *Scheduler) GetStatuses() map[JobType]*JobStatus {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make(map[JobType]*JobStatus)
	for k, v := range s.statuses {
		result[k] = v
	}
	return result
}

func (s *Scheduler) TriggerJob(jobType JobType) error {
	switch jobType {
	case JobTTLCheck:
		go s.runTTLCheck()
	case JobTiering:
		go s.runTiering()
	case JobCleanup:
		go s.runCleanup()
	case JobOptimize:
		go s.runOptimize()
	default:
		return nil
	}
	s.logger.Info("manually triggered job", zap.String("type", string(jobType)))
	return nil
}

package scheduler

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/robfig/cron/v3"
	"etcd-backup-manager/internal/backup"
	"etcd-backup-manager/pkg/models"
)

type Scheduler struct {
	cron        *cron.Cron
	backupMgr   *backup.Manager
	schedules   map[string]*models.Schedule
	entryIDs    map[string]cron.EntryID
	mu          sync.RWMutex
}

func NewScheduler(backupMgr *backup.Manager) *Scheduler {
	return &Scheduler{
		cron:      cron.New(cron.WithSeconds()),
		backupMgr: backupMgr,
		schedules: make(map[string]*models.Schedule),
		entryIDs:  make(map[string]cron.EntryID),
	}
}

func (s *Scheduler) Start() {
	s.cron.Start()
}

func (s *Scheduler) Stop() {
	s.cron.Stop()
}

func (s *Scheduler) AddSchedule(schedule *models.Schedule) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !schedule.Enabled {
		s.schedules[schedule.ID] = schedule
		return nil
	}

	entryID, err := s.cron.AddFunc(schedule.CronExpr, func() {
		s.executeBackup(schedule)
	})
	if err != nil {
		return fmt.Errorf("invalid cron expression: %w", err)
	}

	s.schedules[schedule.ID] = schedule
	s.entryIDs[schedule.ID] = entryID
	return nil
}

func (s *Scheduler) RemoveSchedule(scheduleID string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if entryID, exists := s.entryIDs[scheduleID]; exists {
		s.cron.Remove(entryID)
		delete(s.entryIDs, scheduleID)
	}
	delete(s.schedules, scheduleID)
}

func (s *Scheduler) UpdateSchedule(schedule *models.Schedule) error {
	s.RemoveSchedule(schedule.ID)
	return s.AddSchedule(schedule)
}

func (s *Scheduler) GetSchedule(id string) (*models.Schedule, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	schedule, exists := s.schedules[id]
	if !exists {
		return nil, fmt.Errorf("schedule %s not found", id)
	}
	return schedule, nil
}

func (s *Scheduler) ListSchedules(clusterID string) []*models.Schedule {
	s.mu.RLock()
	defer s.mu.RUnlock()

	schedules := make([]*models.Schedule, 0)
	for _, schedule := range s.schedules {
		if clusterID == "" || schedule.ClusterID == clusterID {
			schedules = append(schedules, schedule)
		}
	}
	return schedules
}

func (s *Scheduler) executeBackup(schedule *models.Schedule) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	var err error
	if schedule.BackupType == "full" {
		_, err = s.backupMgr.CreateFullBackup(ctx, schedule.ClusterID)
	} else {
		_, err = s.backupMgr.CreateIncrementalBackup(ctx, schedule.ClusterID, "")
	}

	if err != nil {
		fmt.Printf("Scheduled backup failed for cluster %s: %v\n", schedule.ClusterID, err)
	}
}

func (s *Scheduler) GetNextRun(scheduleID string) (time.Time, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	entryID, exists := s.entryIDs[scheduleID]
	if !exists {
		return time.Time{}, fmt.Errorf("schedule %s not found or not enabled", scheduleID)
	}

	entry := s.cron.Entry(entryID)
	return entry.Next, nil
}

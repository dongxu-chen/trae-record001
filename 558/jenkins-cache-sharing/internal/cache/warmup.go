package cache

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/jenkins-cache-sharing/internal/model"
	jenkinsclient "github.com/jenkins-cache-sharing/internal/jenkins"
	"github.com/jenkins-cache-sharing/internal/storage"
	"go.uber.org/zap"
)

type WarmupService struct {
	meta          *MetaStore
	vm            *VersionManager
	storage       *storage.ObjectStorage
	jenkins       *jenkinsclient.Client
	tasks         map[string]*model.WarmupTask
	changeEvents  map[string]*model.DependencyChangeEvent
	mu            sync.RWMutex
	workers       int
	autoWarmup    bool
	logger        *zap.Logger
}

func NewWarmupService(meta *MetaStore, vm *VersionManager, objStorage *storage.ObjectStorage, jenkinsClient *jenkinsclient.Client, workers int, logger *zap.Logger) *WarmupService {
	return &WarmupService{
		meta:         meta,
		vm:           vm,
		storage:      objStorage,
		jenkins:      jenkinsClient,
		tasks:        make(map[string]*model.WarmupTask),
		changeEvents: make(map[string]*model.DependencyChangeEvent),
		workers:      workers,
		autoWarmup:   true,
		logger:       logger,
	}
}

func (ws *WarmupService) SetAutoWarmup(enabled bool) {
	ws.autoWarmup = enabled
	ws.logger.Info("auto warmup updated", zap.Bool("enabled", enabled))
}

func (ws *WarmupService) CreateWarmupTask(ctx context.Context, cacheType model.CacheType, sourceJob string, sourceBuild int, targetJobs []string, trigger model.WarmupTrigger, prevHash, currHash string) (*model.WarmupTask, error) {
	task := &model.WarmupTask{
		ID:           generateID(),
		CacheType:    cacheType,
		SourceJob:    sourceJob,
		SourceBuild:  sourceBuild,
		TargetJobs:   targetJobs,
		Status:       "pending",
		Progress:     0,
		Trigger:      trigger,
		PreviousHash: prevHash,
		CurrentHash:  currHash,
		CreatedAt:    time.Now(),
	}

	ws.mu.Lock()
	ws.tasks[task.ID] = task
	ws.mu.Unlock()

	go ws.executeWarmup(task)

	ws.logger.Info("created warmup task",
		zap.String("id", task.ID),
		zap.String("type", string(cacheType)),
		zap.String("source_job", sourceJob),
		zap.String("trigger", string(trigger)),
	)

	return task, nil
}

func (ws *WarmupService) CheckAndTriggerWarmup(
	ctx context.Context,
	cacheType model.CacheType,
	jobName string,
	buildNumber int,
	fileContents map[string]string,
) (*model.WarmupTask, *model.DependencyChangeEvent, error) {
	event, err := ws.vm.CheckDependencyChange(ctx, cacheType, jobName, fileContents)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to check dependency change: %w", err)
	}

	if event == nil {
		ws.logger.Debug("no dependency change detected",
			zap.String("type", string(cacheType)),
			zap.String("job", jobName),
		)
		return nil, nil, nil
	}

	event.BuildNumber = buildNumber

	ws.mu.Lock()
	ws.changeEvents[event.ID] = event
	ws.mu.Unlock()

	ws.logger.Info("dependency change detected",
		zap.String("type", string(cacheType)),
		zap.String("job", jobName),
		zap.String("prev_hash", event.PreviousHash[:12]+"..."),
		zap.String("curr_hash", event.CurrentHash[:12]+"..."),
		zap.Strings("changed_files", event.ChangedFiles),
	)

	if !ws.autoWarmup {
		return nil, event, nil
	}

	targetJobs, err := ws.jenkins.GetDownstreamJobs(ctx, jobName)
	if err != nil {
		ws.logger.Warn("failed to get downstream jobs", zap.Error(err))
		targetJobs = []string{}
	}

	if len(targetJobs) == 0 {
		ws.logger.Info("no downstream jobs to warmup", zap.String("job", jobName))
		return nil, event, nil
	}

	task, err := ws.CreateWarmupTask(
		ctx,
		cacheType,
		jobName,
		buildNumber,
		targetJobs,
		model.WarmupTriggerDependency,
		event.PreviousHash,
		event.CurrentHash,
	)
	if err != nil {
		return nil, event, err
	}

	event.AutoWarmed = true
	event.WarmupTaskID = task.ID

	ws.mu.Lock()
	ws.changeEvents[event.ID] = event
	ws.mu.Unlock()

	return task, event, nil
}

func (ws *WarmupService) GetDependencyEvents(ctx context.Context, cacheType model.CacheType, jobName string) []*model.DependencyChangeEvent {
	ws.mu.RLock()
	defer ws.mu.RUnlock()

	var events []*model.DependencyChangeEvent
	for _, e := range ws.changeEvents {
		if cacheType != "" && e.CacheType != cacheType {
			continue
		}
		if jobName != "" && e.JobName != jobName {
			continue
		}
		events = append(events, e)
	}

	return events
}

func (ws *WarmupService) executeWarmup(task *model.WarmupTask) {
	ctx := context.Background()

	ws.updateTask(task.ID, func(t *model.WarmupTask) {
		t.Status = "running"
	})

	sourceEntries := ws.findSourceEntries(task.CacheType, task.SourceJob, task.SourceBuild)
	if len(sourceEntries) == 0 {
		ws.updateTask(task.ID, func(t *model.WarmupTask) {
			t.Status = "failed"
			t.Error = "no source cache entries found"
			now := time.Now()
			t.FinishedAt = &now
		})
		return
	}

	if task.CurrentHash != "" {
		sourceEntries = ws.filterEntriesByHash(sourceEntries, task.CurrentHash)
		if len(sourceEntries) == 0 {
			ws.updateTask(task.ID, func(t *model.WarmupTask) {
				t.Status = "failed"
				t.Error = "no source entries matching current dependency hash"
				now := time.Now()
				t.FinishedAt = &now
			})
			return
		}
	}

	totalSteps := float64(len(sourceEntries) * len(task.TargetJobs))
	completed := float64(0)

	sem := make(chan struct{}, ws.workers)
	var wg sync.WaitGroup
	var errs []string
	var errMu sync.Mutex

	for _, entry := range sourceEntries {
		for _, targetJob := range task.TargetJobs {
			wg.Add(1)
			sem <- struct{}{}
			go func(entry *model.CacheEntry, targetJob string) {
				defer wg.Done()
				defer func() { <-sem }()

				if err := ws.warmupForJob(ctx, entry, targetJob, task.CurrentHash); err != nil {
					errMu.Lock()
					errs = append(errs, fmt.Sprintf("job %s: %v", targetJob, err))
					errMu.Unlock()
					ws.logger.Error("warmup failed for job",
						zap.String("job", targetJob),
						zap.Error(err),
					)
				}

				completed++
				ws.updateTask(task.ID, func(t *model.WarmupTask) {
					t.Progress = (completed / totalSteps) * 100
				})
			}(entry, targetJob)
		}
	}

	wg.Wait()

	ws.updateTask(task.ID, func(t *model.WarmupTask) {
		now := time.Now()
		t.FinishedAt = &now
		t.Progress = 100
		if len(errs) > 0 {
			t.Status = "partial"
			t.Error = fmt.Sprintf("%d errors occurred", len(errs))
		} else {
			t.Status = "completed"
		}
	})

	ws.logger.Info("warmup task completed",
		zap.String("id", task.ID),
		zap.String("status", task.Status),
		zap.String("trigger", string(task.Trigger)),
	)
}

func (ws *WarmupService) filterEntriesByHash(entries []*model.CacheEntry, hash string) []*model.CacheEntry {
	var filtered []*model.CacheEntry
	for _, e := range entries {
		if e.DependencyHash == hash {
			filtered = append(filtered, e)
		}
	}

	if len(filtered) == 0 {
		return entries
	}
	return filtered
}

func (ws *WarmupService) warmupForJob(ctx context.Context, sourceEntry *model.CacheEntry, targetJob string, depHash string) error {
	existingHash := ws.vm.GetLatestDependencyHash(ctx, sourceEntry.Type, targetJob)
	if existingHash == depHash {
		ws.logger.Debug("target already has same dependency hash, skipping warmup",
			zap.String("job", targetJob),
			zap.String("hash", depHash[:12]+"..."),
		)
		return nil
	}

	reader, size, err := ws.storage.Download(ctx, sourceEntry.ObjectKey)
	if err != nil {
		return fmt.Errorf("failed to download source cache: %w", err)
	}
	defer reader.Close()

	version := fmt.Sprintf("warmup-%d", time.Now().Unix())
	_, err = ws.storage.Upload(ctx, sourceEntry.Type, targetJob, 0, reader, size, version)
	if err != nil {
		return fmt.Errorf("failed to upload warmup cache: %w", err)
	}

	newEntry := &model.CacheEntry{
		Name:             fmt.Sprintf("Warmup from %s", sourceEntry.JobName),
		Type:             sourceEntry.Type,
		Version:          version,
		BuildNumber:      0,
		JobName:          targetJob,
		Size:             size,
		ObjectKey:        storage.BuildObjectKey(sourceEntry.Type, targetJob, 0, version),
		Tags:             []string{"warmup"},
		DependencyHash:   depHash,
		DependencyFiles:  sourceEntry.DependencyFiles,
	}

	_, err = ws.vm.CreateEntry(ctx, newEntry)
	if err != nil {
		return fmt.Errorf("failed to create warmup entry: %w", err)
	}

	return nil
}

func (ws *WarmupService) findSourceEntries(cacheType model.CacheType, sourceJob string, sourceBuild int) []*model.CacheEntry {
	ws.meta.mu.RLock()
	defer ws.meta.mu.RUnlock()

	var entries []*model.CacheEntry
	for _, entry := range ws.meta.entries {
		if entry.Type == cacheType && entry.JobName == sourceJob {
			if sourceBuild == 0 || entry.BuildNumber == sourceBuild {
				entries = append(entries, entry)
			}
		}
	}
	return entries
}

func (ws *WarmupService) GetTask(ctx context.Context, id string) (*model.WarmupTask, error) {
	ws.mu.RLock()
	defer ws.mu.RUnlock()

	task, ok := ws.tasks[id]
	if !ok {
		return nil, fmt.Errorf("warmup task not found: %s", id)
	}
	return task, nil
}

func (ws *WarmupService) ListTasks(ctx context.Context) ([]*model.WarmupTask, error) {
	ws.mu.RLock()
	defer ws.mu.RUnlock()

	var tasks []*model.WarmupTask
	for _, t := range ws.tasks {
		tasks = append(tasks, t)
	}
	return tasks, nil
}

func (ws *WarmupService) updateTask(id string, update func(*model.WarmupTask)) {
	ws.mu.Lock()
	defer ws.mu.Unlock()

	if task, ok := ws.tasks[id]; ok {
		update(task)
	}
}

func (ws *WarmupService) WarmupFromJenkins(ctx context.Context, cacheType model.CacheType, jobName string, buildNumber int) (*model.WarmupTask, error) {
	build, err := ws.jenkins.GetBuild(ctx, jobName, buildNumber)
	if err != nil {
		return nil, fmt.Errorf("failed to get jenkins build: %w", err)
	}

	cacheKey := fmt.Sprintf("%s-cache", cacheType)
	artifactName := ""
	for _, artifact := range build.Artifacts {
		if containsCacheKeyword(artifact.FileName, cacheType) {
			artifactName = artifact.FileName
			break
		}
	}

	if artifactName == "" {
		cacheKey = ""
		for _, param := range build.Parameters {
			if param == string(cacheType) {
				cacheKey = string(cacheType)
				break
			}
		}
	}

	_ = cacheKey

	targetJobs, err := ws.jenkins.GetDownstreamJobs(ctx, jobName)
	if err != nil {
		ws.logger.Warn("failed to get downstream jobs, using empty list", zap.Error(err))
		targetJobs = []string{}
	}

	return ws.CreateWarmupTask(ctx, cacheType, jobName, buildNumber, targetJobs, model.WarmupTriggerBuildComplete, "", "")
}

func containsCacheKeyword(filename string, cacheType model.CacheType) bool {
	switch cacheType {
	case model.CacheTypeMaven:
		return contains(filename, ".m2") || contains(filename, "maven")
	case model.CacheTypeNPM:
		return contains(filename, "npm") || contains(filename, "node_modules")
	case model.CacheTypeGradle:
		return contains(filename, ".gradle") || contains(filename, "gradle")
	}
	return false
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsSubstr(s, substr))
}

func containsSubstr(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

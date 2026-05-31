package cache

import (
	"context"
	"sort"
	"sync"
	"time"

	"github.com/jenkins-cache-sharing/internal/model"
	"go.uber.org/zap"
)

type SharingManager struct {
	meta    *MetaStore
	vm      *VersionManager
	groups  map[string]*model.ProjectGroup
	mu      sync.RWMutex
	logger  *zap.Logger
}

func NewSharingManager(meta *MetaStore, vm *VersionManager, logger *zap.Logger) *SharingManager {
	return &SharingManager{
		meta:   meta,
		vm:     vm,
		groups: make(map[string]*model.ProjectGroup),
		logger: logger,
	}
}

func (sm *SharingManager) CreateGroup(ctx context.Context, group *model.ProjectGroup) (*model.ProjectGroup, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	if group.ID == "" {
		group.ID = generateID()
	}
	now := time.Now()
	group.CreatedAt = now
	group.UpdatedAt = now

	if group.MinSimilarity == 0 {
		group.MinSimilarity = 0.7
	}

	sm.groups[group.ID] = group

	if err := sm.meta.save(); err != nil {
		sm.logger.Error("failed to save metadata", zap.Error(err))
	}

	sm.logger.Info("created project group",
		zap.String("id", group.ID),
		zap.String("name", group.Name),
		zap.Int("jobs", len(group.Jobs)),
	)

	return group, nil
}

func (sm *SharingManager) UpdateGroup(ctx context.Context, id string, updates func(*model.ProjectGroup)) (*model.ProjectGroup, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	group, ok := sm.groups[id]
	if !ok {
		return nil, nil
	}

	updates(group)
	group.UpdatedAt = time.Now()

	if err := sm.meta.save(); err != nil {
		sm.logger.Error("failed to save metadata", zap.Error(err))
	}

	sm.logger.Info("updated project group", zap.String("id", id))
	return group, nil
}

func (sm *SharingManager) DeleteGroup(ctx context.Context, id string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	delete(sm.groups, id)

	if err := sm.meta.save(); err != nil {
		sm.logger.Error("failed to save metadata", zap.Error(err))
	}

	sm.logger.Info("deleted project group", zap.String("id", id))
	return nil
}

func (sm *SharingManager) GetGroup(ctx context.Context, id string) (*model.ProjectGroup, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	group, ok := sm.groups[id]
	if !ok {
		return nil, nil
	}
	return group, nil
}

func (sm *SharingManager) ListGroups(ctx context.Context) ([]*model.ProjectGroup, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var groups []*model.ProjectGroup
	for _, g := range sm.groups {
		groups = append(groups, g)
	}

	sort.Slice(groups, func(i, j int) bool {
		return groups[i].CreatedAt.After(groups[j].CreatedAt)
	})

	return groups, nil
}

func (sm *SharingManager) FindSimilarCaches(
	ctx context.Context,
	cacheType model.CacheType,
	jobName string,
	dependencyHash string,
	depFiles []model.DependencyFileHash,
) []*model.SimilarityMatch {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var groupJobs []string
	for _, group := range sm.groups {
		if !group.SharingEnabled {
			continue
		}
		if len(group.CacheTypes) > 0 {
			hasType := false
			for _, t := range group.CacheTypes {
				if t == cacheType {
					hasType = true
					break
				}
			}
			if !hasType {
				continue
			}
		}
		hasJob := false
		for _, j := range group.Jobs {
			if j == jobName {
				hasJob = true
				break
			}
		}
		if hasJob {
			groupJobs = append(groupJobs, group.Jobs...)
		}
	}

	if len(groupJobs) == 0 {
		return nil
	}

	jobSet := make(map[string]bool)
	for _, j := range groupJobs {
		if j != jobName {
			jobSet[j] = true
		}
	}

	sm.meta.mu.RLock()
	defer sm.meta.mu.RUnlock()

	depFileMap := make(map[string]string)
	for _, f := range depFiles {
		depFileMap[f.Path] = f.Hash
	}

	var matches []*model.SimilarityMatch
	for _, entry := range sm.meta.entries {
		if entry.Type != cacheType || entry.Status != model.CacheStatusActive {
			continue
		}
		if !jobSet[entry.JobName] {
			continue
		}

		similarity := calculateSimilarity(depFileMap, entry.DependencyFiles)

		minSim := 0.7
		for _, g := range sm.groups {
			if g.SharingEnabled {
				hasJob := false
				for _, j := range g.Jobs {
					if j == jobName || j == entry.JobName {
						hasJob = true
						break
					}
				}
				if hasJob && g.MinSimilarity > 0 {
					minSim = g.MinSimilarity
				}
			}
		}

		if similarity >= minSim {
			matches = append(matches, &model.SimilarityMatch{
				SourceJob:    entry.JobName,
				TargetJob:    jobName,
				CacheType:    cacheType,
				Similarity:   similarity,
				MatchedHash:  entry.DependencyHash,
				CacheEntryID: entry.ID,
				CacheSize:    entry.Size,
			})
		}
	}

	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Similarity > matches[j].Similarity
	})

	return matches
}

func (sm *SharingManager) AddJobToGroup(ctx context.Context, groupID, jobName string) error {
	return sm.UpdateGroup(ctx, groupID, func(g *model.ProjectGroup) {
		for _, j := range g.Jobs {
			if j == jobName {
				return
			}
		}
		g.Jobs = append(g.Jobs, jobName)
	})
}

func (sm *SharingManager) RemoveJobFromGroup(ctx context.Context, groupID, jobName string) error {
	return sm.UpdateGroup(ctx, groupID, func(g *model.ProjectGroup) {
		for i, j := range g.Jobs {
			if j == jobName {
				g.Jobs = append(g.Jobs[:i], g.Jobs[i+1:]...)
				break
			}
		}
	})
}

func (sm *SharingManager) GetGroupsForJob(ctx context.Context, jobName string) []*model.ProjectGroup {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var groups []*model.ProjectGroup
	for _, g := range sm.groups {
		for _, j := range g.Jobs {
			if j == jobName {
				groups = append(groups, g)
				break
			}
		}
	}
	return groups
}

func calculateSimilarity(source map[string]string, target []model.DependencyFileHash) float64 {
	if len(source) == 0 || len(target) == 0 {
		return 0
	}

	targetMap := make(map[string]string)
	for _, f := range target {
		targetMap[f.Path] = f.Hash
	}

	matched := 0
	total := len(source)

	for path, sourceHash := range source {
		if targetHash, exists := targetMap[path]; exists {
			if sourceHash == targetHash {
				matched++
			}
		}
	}

	return float64(matched) / float64(total)
}

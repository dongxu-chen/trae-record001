package geo

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"github.com/coldstart-optimizer/coldstart/internal/model"
)

type ReplicationConfig struct {
	MaxBandwidthMB int
	MinLatencyMs   int64
	MaxRegions     int
	ParallelCopies int
}

func DefaultReplicationConfig() ReplicationConfig {
	return ReplicationConfig{
		MaxBandwidthMB: 500,
		MinLatencyMs:   1,
		MaxRegions:     6,
		ParallelCopies: 3,
	}
}

type ReplicationState struct {
	Region      string
	Available   bool
	LocalPath   string
	ReplicatedAt time.Time
	Checksum    string
	LatencyMs   int64
}

type RegionStore struct {
	mu      sync.RWMutex
	regions map[string]*model.GeoRegion
	states  map[string]map[string]*ReplicationState
}

func NewRegionStore() *RegionStore {
	return &RegionStore{
		regions: make(map[string]*model.GeoRegion),
		states:  make(map[string]map[string]*ReplicationState),
	}
}

func (s *RegionStore) RegisterRegion(r *model.GeoRegion) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.regions[r.ID] = r
}

func (s *RegionStore) AllRegions() []*model.GeoRegion {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var out []*model.GeoRegion
	for _, r := range s.regions {
		out = append(out, r)
	}
	return out
}

func (s *RegionStore) FindRegionByZone(zone string) *model.GeoRegion {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, r := range s.regions {
		if r.Zone == zone || r.Region == zone {
			return r
		}
	}
	return nil
}

func (s *RegionStore) SetState(snapshotID, regionID string, st *ReplicationState) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.states[snapshotID]; !ok {
		s.states[snapshotID] = make(map[string]*ReplicationState)
	}
	s.states[snapshotID][regionID] = st
}

func (s *RegionStore) GetState(snapshotID, regionID string) *ReplicationState {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if m, ok := s.states[snapshotID]; ok {
		return m[regionID]
	}
	return nil
}

func (s *RegionStore) IsAvailable(snapshotID, regionID string) bool {
	st := s.GetState(snapshotID, regionID)
	return st != nil && st.Available
}

type Replicator struct {
	store  *RegionStore
	config ReplicationConfig
}

func NewReplicator(store *RegionStore, config ReplicationConfig) *Replicator {
	return &Replicator{store: store, config: config}
}

func (r *Replicator) BuildPlan(ctx context.Context, function, snapshotID, sourceRegion string, sizeBytes int64, regions []*model.GeoRegion) (*model.GeoReplicationPlan, error) {
	if len(regions) == 0 {
		regions = r.store.AllRegions()
	}
	if len(regions) > r.config.MaxRegions {
		sort.SliceStable(regions, func(i, k int) bool {
			return regions[i].LatencyMs < regions[k].LatencyMs
		})
		regions = regions[:r.config.MaxRegions]
	}

	plan := &model.GeoReplicationPlan{
		Function:     function,
		SnapshotID:   snapshotID,
		SourceRegion: sourceRegion,
		TotalSize:    sizeBytes * int64(len(regions)),
	}

	for _, target := range regions {
		if target.Region == sourceRegion {
			continue
		}
		bw := target.BandwidthMB
		if bw <= 0 {
			bw = int64(r.config.MaxBandwidthMB)
		}
		transferMs := (sizeBytes / 1024 / 1024) * 1000 / bw
		if transferMs < target.LatencyMs {
			transferMs = target.LatencyMs
		}

		geoSnap := model.GeoSnapshot{
			SnapshotID:   snapshotID,
			SourceRegion: sourceRegion,
			TargetRegion: *target,
			SizeBytes:    sizeBytes,
			TransferMs:   transferMs,
			LocalPath:    fmt.Sprintf("/var/cache/coldstart/geo/%s/%s", target.Region, snapshotID),
			Available:    false,
		}
		plan.Targets = append(plan.Targets, geoSnap)
		plan.TotalTransferMs += transferMs
	}
	return plan, nil
}

func (r *Replicator) Execute(ctx context.Context, plan *model.GeoReplicationPlan) error {
	for i := range plan.Targets {
		target := &plan.Targets[i]
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		target.ReplicatedAt = time.Now()
		target.Available = true
		r.store.SetState(plan.SnapshotID, target.TargetRegion.ID, &ReplicationState{
			Region:       target.TargetRegion.Region,
			Available:    true,
			LocalPath:    target.LocalPath,
			ReplicatedAt: target.ReplicatedAt,
			LatencyMs:    target.TransferMs,
		})
	}
	return nil
}

func (r *Replicator) LocalLoadPath(snapshotID, regionID string) string {
	st := r.store.GetState(snapshotID, regionID)
	if st == nil || !st.Available {
		return ""
	}
	return st.LocalPath
}

type RegionalScheduler struct {
	replicator *Replicator
}

func NewRegionalScheduler(replicator *Replicator) *RegionalScheduler {
	return &RegionalScheduler{replicator: replicator}
}

func (s *RegionalScheduler) ResolveFastestPath(snapshotID, requestRegion string) (string, string, bool) {
	st := s.replicator.store.GetState(snapshotID, requestRegion)
	if st != nil && st.Available {
		return st.LocalPath, requestRegion, true
	}
	regions := s.replicator.store.AllRegions()
	bestPath := ""
	bestRegion := ""
	minLatency := int64(1<<62 - 1)
	for _, r := range regions {
		st2 := s.replicator.store.GetState(snapshotID, r.ID)
		if st2 != nil && st2.Available {
			if r.LatencyMs < minLatency {
				minLatency = r.LatencyMs
				bestPath = st2.LocalPath
				bestRegion = r.Region
			}
		}
	}
	if bestPath != "" {
		return bestPath, bestRegion, true
	}
	return "", "", false
}

func DefaultRegionSet() []*model.GeoRegion {
	return []*model.GeoRegion{
		{ID: "cn-sh", Name: "China Shanghai", Region: "cn-shanghai", Zone: "cn-shanghai-a", Endpoint: "https://snapshot.cn-sh.coldstart.local", BandwidthMB: 500, LatencyMs: 1, PriceFactor: 1.0},
		{ID: "cn-bj", Name: "China Beijing", Region: "cn-beijing", Zone: "cn-beijing-a", Endpoint: "https://snapshot.cn-bj.coldstart.local", BandwidthMB: 400, LatencyMs: 25, PriceFactor: 1.05},
		{ID: "cn-gz", Name: "China Guangzhou", Region: "cn-guangzhou", Zone: "cn-guangzhou-a", Endpoint: "https://snapshot.cn-gz.coldstart.local", BandwidthMB: 400, LatencyMs: 30, PriceFactor: 1.05},
		{ID: "cn-sz", Name: "China Shenzhen", Region: "cn-shenzhen", Zone: "cn-shenzhen-a", Endpoint: "https://snapshot.cn-sz.coldstart.local", BandwidthMB: 400, LatencyMs: 20, PriceFactor: 1.03},
		{ID: "cn-hk", Name: "Hong Kong", Region: "cn-hongkong", Zone: "cn-hongkong-a", Endpoint: "https://snapshot.cn-hk.coldstart.local", BandwidthMB: 300, LatencyMs: 45, PriceFactor: 1.15},
		{ID: "ap-sg", Name: "Singapore", Region: "ap-southeast-1", Zone: "ap-southeast-1a", Endpoint: "https://snapshot.ap-sg.coldstart.local", BandwidthMB: 200, LatencyMs: 65, PriceFactor: 1.25},
	}
}

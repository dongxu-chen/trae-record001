package relay

import (
	"context"
	"io"
	"net/http"
	"sync"
	"time"

	"registry-sync/pkg/progress"
	"registry-sync/pkg/registry"
)

type RelayNode struct {
	client       registry.RegistryClient
	url          string
	region       string
	cacheBlobs   map[string]bool
	cacheMu        sync.RWMutex
	cacheExpiry   time.Duration
	cacheTimestamps map[string]time.Time
}

type RelayManager struct {
	nodes         []*RelayNode
	clientCache   map[string]*RelayNode
	primaryNode   *RelayNode
}

type RelaySyncer struct {
	sourceClient  registry.RegistryClient
	targetClient  registry.RegistryClient
	relayManager   *RelayManager
	progress        *progress.SyncProgress
	rateLimiter   *registry.DynamicRateLimiter
}

func NewRelayNode(client registry.RegistryClient, url, region string) *RelayNode {
	return &RelayNode{
		client:          client,
		url:             url,
		region:          region,
		cacheBlobs:    make(map[string]bool),
		cacheTimestamps: make(map[string]time.Time),
		cacheExpiry:   24 * time.Hour,
	}
}

func NewRelayManager() *RelayManager {
	return &RelayManager{
		clientCache: make(map[string]*RelayNode),
	}
}

func (rm *RelayManager) AddNode(node *RelayNode) {
	rm.nodes = append(rm.nodes, node)
	rm.clientCache[node.region] = node
}

func (rm *RelayManager) SelectOptimalNode(sourceRegion, targetRegion string) *RelayNode {
	if len(rm.nodes) == 0 {
		return nil
	}

	if rm.primaryNode != nil {
		return rm.primaryNode
	}

	var bestNode *RelayNode
	for _, node := range rm.nodes {
		if bestNode == nil {
			bestNode = node
			continue
		}
	}

	return bestNode
}

func (rn *RelayNode) HasCachedBlob(digest string) bool {
	rn.cacheMu.RLock()
	defer rn.cacheMu.RUnlock()

	cached, ok := rn.cacheBlobs[digest]
	if !ok {
		return false
	}

	ts, tsOk := rn.cacheTimestamps[digest]
	if !tsOk || time.Since(ts) > rn.cacheExpiry {
		delete(rn.cacheBlobs, digest)
		delete(rn.cacheTimestamps, digest)
		return false
	}

	return cached
}

func (rn *RelayNode) MarkBlobCached(digest string) {
	rn.cacheMu.Lock()
	defer rn.cacheMu.Unlock()

	rn.cacheBlobs[digest] = true
	rn.cacheTimestamps[digest] = time.Now()
}

func (rn *RelayNode) GetClient() registry.RegistryClient {
	return rn.client
}

func (rn *RelayNode) GetURL() string {
	return rn.url
}

func NewRelaySyncer(
	sourceClient, targetClient registry.RegistryClient,
	relayManager *RelayManager,
	prog *progress.SyncProgress,
	rateLimiter *registry.DynamicRateLimiter,
) *RelaySyncer {
	return &RelaySyncer{
		sourceClient: sourceClient,
		targetClient: targetClient,
		relayManager: relayManager,
		progress:     prog,
		rateLimiter: rateLimiter,
	}
}

func (rs *RelaySyncer) GetRelayManager() *RelayManager {
	return rs.relayManager
}

func (rs *RelaySyncer) SyncBlobViaRelay(
	ctx context.Context,
	sourceRepo, targetRepo, digest string,
	relayNode *RelayNode,
) error {
	if relayNode == nil {
		return rs.directSyncBlob(ctx, sourceRepo, targetRepo, digest)
	}

	if relayNode.HasCachedBlob(digest) {
		exists, err := relayNode.GetClient().BlobExists(ctx, sourceRepo, digest)
		if err == nil && exists {
			return rs.syncFromRelay(ctx, targetRepo, digest, relayNode)
		}
	}

	if err := rs.syncToRelay(ctx, sourceRepo, digest, relayNode); err != nil {
		return err
	}

	relayNode.MarkBlobCached(digest)

	return rs.syncFromRelay(ctx, targetRepo, digest, relayNode)
}

func (rs *RelaySyncer) directSyncBlob(
	ctx context.Context,
	sourceRepo, targetRepo, digest string,
) error {
	blobReader, size, err := rs.sourceClient.GetBlob(ctx, sourceRepo, digest)
	if err != nil {
		return err
	}
	defer blobReader.Close()

	var reader io.Reader = blobReader

	if rs.rateLimiter != nil {
		reader = registry.NewRateLimitedReader(reader, rs.rateLimiter)
	}

	progressWriter := progress.NewProgressWriter(rs.progress, sourceRepo, "")
	teeReader := io.TeeReader(reader, progressWriter)

	pushStart := time.Now()
	if err := rs.targetClient.PushBlob(ctx, targetRepo, digest, teeReader, size); err != nil {
		return err
	}

	if rs.rateLimiter != nil {
		rs.rateLimiter.RecordLatency(time.Since(pushStart))
		rs.rateLimiter.RecordTransfer(progressWriter.Written())
	}

	return nil
}

func (rs *RelaySyncer) syncToRelay(
	ctx context.Context,
	sourceRepo, digest string,
	relayNode *RelayNode,
) error {
	blobReader, size, err := rs.sourceClient.GetBlob(ctx, sourceRepo, digest)
	if err != nil {
		return err
	}
	defer blobReader.Close()

	var reader io.Reader = blobReader

	if rs.rateLimiter != nil {
		reader = registry.NewRateLimitedReader(reader, rs.rateLimiter)
	}

	progressWriter := progress.NewProgressWriter(rs.progress, sourceRepo, "")
	teeReader := io.TeeReader(reader, progressWriter)

	pushStart := time.Now()
	if err := relayNode.GetClient().PushBlob(ctx, sourceRepo, digest, teeReader, size); err != nil {
		return err
	}

	if rs.rateLimiter != nil {
		rs.rateLimiter.RecordLatency(time.Since(pushStart))
		rs.rateLimiter.RecordTransfer(progressWriter.Written())
	}

	return nil
}

func (rs *RelaySyncer) syncFromRelay(
	ctx context.Context,
	targetRepo, digest string,
	relayNode *RelayNode,
) error {
	blobReader, size, err := relayNode.GetClient().GetBlob(ctx, targetRepo, digest)
	if err != nil {
		return err
	}
	defer blobReader.Close()

	var reader io.Reader = blobReader

	if rs.rateLimiter != nil {
		reader = registry.NewRateLimitedReader(reader, rs.rateLimiter)
	}

	progressWriter := progress.NewProgressWriter(rs.progress, "", "")
	teeReader := io.TeeReader(reader, progressWriter)

	pushStart := time.Now()
	if err := rs.targetClient.PushBlob(ctx, targetRepo, digest, teeReader, size); err != nil {
		return err
	}

	if rs.rateLimiter != nil {
		rs.rateLimiter.RecordLatency(time.Since(pushStart))
		rs.rateLimiter.RecordTransfer(progressWriter.Written())
	}

	return nil
}

func (rs *RelaySyncer) CleanupExpiredCache() {
	for _, node := range rs.relayManager.nodes {
		node.cacheMu.Lock()
		now := time.Now()
		for digest, ts := range node.cacheTimestamps {
			if now.Sub(ts) > node.cacheExpiry {
				delete(node.cacheBlobs, digest)
				delete(node.cacheTimestamps, digest)
			}
		}
		node.cacheMu.Unlock()
	}
}

type NetworkProbeResult struct {
		SourceRegion  string
		TargetRegion string
		Latency    time.Duration
		Throughput int64
		Timestamp  time.Time
	}

func ProbeNetwork(
	ctx context.Context,
	sourceURL, targetURL string,
	sourceRegion, targetRegion string,
) *NetworkProbeResult {
	start := time.Now()
	client := &http.Client{Timeout: 10 * time.Second}
	
	req, err := http.NewRequestWithContext(ctx, "HEAD", targetURL, nil)
	if err != nil {
		return &NetworkProbeResult{
			SourceRegion:  sourceRegion,
			TargetRegion: targetRegion,
			Latency:    -1,
			Timestamp:  time.Now(),
		}
	}

	resp, err := client.Do(req)
	latency := time.Since(start)
	
	if err != nil {
		return &NetworkProbeResult{
			SourceRegion:  sourceRegion,
			TargetRegion: targetRegion,
			Latency:    -1,
			Timestamp:  time.Now(),
		}
	}
	defer resp.Body.Close()

	return &NetworkProbeResult{
		SourceRegion:  sourceRegion,
		TargetRegion: targetRegion,
		Latency:    latency,
		Timestamp:  time.Now(),
	}
}

func SelectOptimalRelay(
	probeResults []*NetworkProbeResult,
	relayNodes []*RelayNode,
) *RelayNode {
	if len(relayNodes) == 0 {
		return nil
	}

	bestIndex := 0
	bestLatency := time.Duration(1<<63 - 1)

	for _, result := range probeResults {
		if result.Latency > 0 && result.Latency < bestLatency {
			for i, node := range relayNodes {
				if node.region == result.TargetRegion {
					bestIndex = i
					bestLatency = result.Latency
					break
				}
			}
		}
	}

	if bestLatency == time.Duration(1<<63-1) {
		return relayNodes[0]
	}

	return relayNodes[bestIndex]
}

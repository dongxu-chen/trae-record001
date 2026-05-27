package sync

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"strings"
	"sync"
	"time"

	"golang.org/x/sync/semaphore"
	"registry-sync/pkg/audit"
	"registry-sync/pkg/config"
	"registry-sync/pkg/filter"
	"registry-sync/pkg/progress"
	"registry-sync/pkg/registry"
	"registry-sync/pkg/relay"
)

type ImageSyncer struct {
	sourceClient registry.RegistryClient
	targetClient registry.RegistryClient
	filter       *filter.Filter
	progress     *progress.SyncProgress
	rateLimiter  *registry.DynamicRateLimiter
	semaphore    *semaphore.Weighted
	sourcePrefix string
	targetPrefix string
	incremental  bool
	verifyDigest bool
	dryRun       bool
	auditLogger  *audit.AuditLogger
	relaySyncer  *relay.RelaySyncer
	cleanupConfig config.CleanupConfig
}

func NewImageSyncer(
	sourceClient, targetClient registry.RegistryClient,
	syncConfig config.SyncConfig,
	filter *filter.Filter,
	progress *progress.SyncProgress,
) (*ImageSyncer, error) {
	maxConcurrent := int64(syncConfig.RateLimit.MaxConcurrent)
	if maxConcurrent <= 0 {
		maxConcurrent = 5
	}

	var rateLimiter *registry.DynamicRateLimiter
	if syncConfig.RateLimit.BytesPerSec > 0 {
		rateLimiter = registry.NewDynamicRateLimiter(
			syncConfig.RateLimit.BytesPerSec,
			syncConfig.RateLimit.BytesPerSec*2,
			syncConfig.RateLimit.BytesPerSec/4,
		)
	}

	var auditLogger *audit.AuditLogger
	if syncConfig.Audit.Enabled {
		var err error
		auditLogger, err = audit.NewAuditLogger(audit.AuditLogConfig{
			LogPath:   syncConfig.Audit.LogPath,
			Operator:  syncConfig.Audit.Operator,
			BatchSize: syncConfig.Audit.BatchSize,
		})
		if err != nil {
			return nil, fmt.Errorf("failed to create audit logger: %w", err)
		}
	}

	var relaySyncer *relay.RelaySyncer
	if len(syncConfig.RelayNodes) > 0 {
		relayManager := relay.NewRelayManager()
		for _, nodeConfig := range syncConfig.RelayNodes {
			nodeRegistryConfig := &config.RegistryConfig{
				Name:     nodeConfig.Name,
				Type:     nodeConfig.Type,
				URL:      nodeConfig.URL,
				Username: nodeConfig.Username,
				Password: nodeConfig.Password,
				Region:   nodeConfig.Region,
				Insecure: nodeConfig.Insecure,
			}
			nodeClient, err := registry.NewClient(nodeRegistryConfig)
			if err != nil {
				return nil, fmt.Errorf("failed to create relay node client: %w", err)
			}
			relayNode := relay.NewRelayNode(nodeClient, nodeConfig.URL, nodeConfig.Region)
			relayManager.AddNode(relayNode)
		}
		relaySyncer = relay.NewRelaySyncer(sourceClient, targetClient, relayManager, progress, rateLimiter)
	}

	return &ImageSyncer{
		sourceClient: sourceClient,
		targetClient: targetClient,
		filter:       filter,
		progress:     progress,
		rateLimiter:  rateLimiter,
		semaphore:    semaphore.NewWeighted(maxConcurrent),
		sourcePrefix: syncConfig.SourcePrefix,
		targetPrefix: syncConfig.TargetPrefix,
		incremental:  syncConfig.Incremental,
		verifyDigest: syncConfig.VerifyDigest,
		dryRun:       syncConfig.DryRun,
		auditLogger:  auditLogger,
		relaySyncer:  relaySyncer,
		cleanupConfig: syncConfig.Cleanup,
	}, nil
}

func (s *ImageSyncer) SyncAll(ctx context.Context) error {
	s.progress.Start()
	defer s.progress.Finish()

	if s.auditLogger != nil {
		defer s.auditLogger.Flush()
	}

	sourceRepos, err := s.sourceClient.ListRepositories(ctx, s.sourcePrefix)
	if err != nil {
		return fmt.Errorf("failed to list source repositories: %w", err)
	}

	sourceRepos = s.filter.FilterRepositories(sourceRepos)

	var wg sync.WaitGroup
	errChan := make(chan error, len(sourceRepos))

	for _, sourceRepo := range sourceRepos {
		targetRepo := s.mapRepository(sourceRepo)

		tags, err := s.sourceClient.ListTags(ctx, sourceRepo)
		if err != nil {
			return fmt.Errorf("failed to list tags for %s: %w", sourceRepo, err)
		}

		tags = s.filter.FilterTags(tags)

		for _, tag := range tags {
			s.progress.AddImage(sourceRepo, tag, targetRepo, tag)

			wg.Add(1)
			go func(sourceRepo, targetRepo, tag string) {
				defer wg.Done()

				if err := s.semaphore.Acquire(ctx, 1); err != nil {
					errChan <- err
					return
				}
				defer s.semaphore.Release(1)

				syncStart := time.Now()
				err := s.SyncImage(ctx, sourceRepo, targetRepo, tag)
				duration := time.Since(syncStart)

				if err != nil {
					s.progress.FailImage(sourceRepo, tag, err)
					if s.auditLogger != nil {
						s.auditLogger.LogSync(sourceRepo, tag, targetRepo, tag, "", 0, duration, err)
					}
					errChan <- fmt.Errorf("failed to sync %s:%s: %w", sourceRepo, tag, err)
				}
			}(sourceRepo, targetRepo, tag)
		}
	}

	wg.Wait()
	close(errChan)

	var errors []error
	for err := range errChan {
		errors = append(errors, err)
	}

	if len(errors) > 0 {
		return fmt.Errorf("sync completed with %d errors: %v", len(errors), errors[0])
	}

	if s.cleanupConfig.Enabled {
		if err := s.CleanupDeletedImages(ctx, sourceRepos); err != nil {
			return fmt.Errorf("cleanup failed: %w", err)
		}
	}

	return nil
}

func (s *ImageSyncer) SyncImage(ctx context.Context, sourceRepo, targetRepo, tag string) error {
	syncStart := time.Now()

	sourceManifest, err := s.sourceClient.GetManifest(ctx, sourceRepo, tag)
	if err != nil {
		return fmt.Errorf("failed to get source manifest: %w", err)
	}

	var manifestData map[string]interface{}
	if err := json.Unmarshal(sourceManifest.Content, &manifestData); err != nil {
		return fmt.Errorf("failed to parse manifest: %w", err)
	}

	layers, ok := manifestData["layers"].([]interface{})
	if !ok {
		return fmt.Errorf("invalid manifest format: no layers")
	}

	needSync := false

	if config, ok := manifestData["config"].(map[string]interface{}); ok {
		configDigest := config["digest"].(string)
		synced, err := s.syncBlobIfNeeded(ctx, sourceRepo, targetRepo, configDigest)
		if err != nil {
			return fmt.Errorf("failed to sync config blob: %w", err)
		}
		if synced {
			needSync = true
		}
	}

	for _, layer := range layers {
		layerMap := layer.(map[string]interface{})
		layerDigest := layerMap["digest"].(string)
		synced, err := s.syncBlobIfNeeded(ctx, sourceRepo, targetRepo, layerDigest)
		if err != nil {
			return fmt.Errorf("failed to sync layer %s: %w", layerDigest, err)
		}
		if synced {
			needSync = true
		}
	}

	if !needSync && s.incremental {
		sourceInfo, err := s.sourceClient.GetImageInfo(ctx, sourceRepo, tag)
		if err != nil {
			return err
		}

		targetExists, err := s.targetClient.ManifestExists(ctx, targetRepo, tag)
		if err != nil {
			return err
		}

		if targetExists {
			targetInfo, err := s.targetClient.GetImageInfo(ctx, targetRepo, tag)
			if err == nil && sourceInfo.Digest == targetInfo.Digest {
				s.progress.SkipImage(sourceRepo, tag)
				if s.auditLogger != nil {
					s.auditLogger.LogSkip(sourceRepo, tag, "Image already exists with same digest")
				}
				return nil
			}
		}
	}

	if !s.dryRun {
		pushStart := time.Now()
		if err := s.targetClient.PushManifest(ctx, targetRepo, tag, sourceManifest); err != nil {
			return fmt.Errorf("failed to push manifest: %w", err)
		}
		pushDuration := time.Since(pushStart)

		if s.rateLimiter != nil {
			s.rateLimiter.RecordLatency(pushDuration)
		}

		if s.auditLogger != nil {
			s.auditLogger.LogPush(targetRepo, tag, sourceManifest.Digest, sourceManifest.Digest, pushDuration, nil)
		}

		if s.verifyDigest {
			if err := s.verifyManifest(ctx, sourceRepo, targetRepo, tag); err != nil {
				return fmt.Errorf("digest verification failed: %w", err)
			}
		}
	}

	duration := time.Since(syncStart)
	s.progress.CompleteImage(sourceRepo, tag)

	if s.auditLogger != nil {
		s.auditLogger.LogSync(sourceRepo, tag, targetRepo, tag, sourceManifest.Digest, 0, duration, nil)
	}

	return nil
}

func (s *ImageSyncer) syncBlobIfNeeded(ctx context.Context, sourceRepo, targetRepo, digest string) (bool, error) {
	exists, err := s.targetClient.BlobExists(ctx, targetRepo, digest)
	if err != nil {
		return false, err
	}
	if exists {
		return false, nil
	}

	if s.dryRun {
		return true, nil
	}

	if s.relaySyncer != nil {
		relayNode := s.relaySyncer.GetRelayManager().SelectOptimalNode("", "")
		if relayNode != nil {
			relayStart := time.Now()
			err := s.relaySyncer.SyncBlobViaRelay(ctx, sourceRepo, targetRepo, digest, relayNode)
			relayDuration := time.Since(relayStart)
			
			if s.auditLogger != nil {
				s.auditLogger.LogRelay(sourceRepo, targetRepo, digest, relayNode.GetURL(), "sync", relayDuration, err)
			}
			
			if err != nil {
				return false, err
			}
			return true, nil
		}
	}

	return s.directSyncBlob(ctx, sourceRepo, targetRepo, digest)
}

func (s *ImageSyncer) directSyncBlob(ctx context.Context, sourceRepo, targetRepo, digest string) (bool, error) {
	blobReader, size, err := s.sourceClient.GetBlob(ctx, sourceRepo, digest)
	if err != nil {
		return false, err
	}
	defer blobReader.Close()

	var reader io.Reader = blobReader

	if s.rateLimiter != nil {
		reader = registry.NewRateLimitedReader(reader, s.rateLimiter)
	}

	progressWriter := progress.NewProgressWriter(s.progress, sourceRepo, "")
	teeReader := io.TeeReader(reader, progressWriter)

	pushStart := time.Now()
	if err := s.targetClient.PushBlob(ctx, targetRepo, digest, teeReader, size); err != nil {
		return false, err
	}

	pushDuration := time.Since(pushStart)

	if s.rateLimiter != nil {
		s.rateLimiter.RecordLatency(pushDuration)
		s.rateLimiter.RecordTransfer(progressWriter.Written())
	}

	return true, nil
}

func (s *ImageSyncer) verifyManifest(ctx context.Context, sourceRepo, targetRepo, tag string) error {
	sourceManifest, err := s.sourceClient.GetManifest(ctx, sourceRepo, tag)
	if err != nil {
		return err
	}

	targetManifest, err := s.targetClient.GetManifest(ctx, targetRepo, tag)
	if err != nil {
		return err
	}

	verified := sourceManifest.Digest == targetManifest.Digest
	
	if s.auditLogger != nil {
		s.auditLogger.LogVerify(targetRepo, tag, targetManifest.Digest, verified, nil)
	}

	if !verified {
		return fmt.Errorf("manifest digest mismatch: source=%s, target=%s",
			sourceManifest.Digest, targetManifest.Digest)
	}

	return nil
}

func (s *ImageSyncer) CleanupDeletedImages(ctx context.Context, sourceRepos []string) error {
	fmt.Println("Starting cleanup of deleted images...")

	for _, sourceRepo := range sourceRepos {
		targetRepo := s.mapRepository(sourceRepo)

		targetTags, err := s.targetClient.ListTags(ctx, targetRepo)
		if err != nil {
			fmt.Printf("Failed to list target tags for %s: %v\n", targetRepo, err)
			continue
		}

		sourceTagSet := make(map[string]bool)
		sourceTags, err := s.sourceClient.ListTags(ctx, sourceRepo)
		if err != nil {
			fmt.Printf("Failed to list source tags for %s: %v\n", sourceRepo, err)
			continue
		}
		for _, tag := range sourceTags {
			sourceTagSet[tag] = true
		}

		for _, targetTag := range targetTags {
			if !sourceTagSet[targetTag] {
				if s.cleanupConfig.DryRun {
					fmt.Printf("[DRY RUN] Would delete: %s:%s\n", targetRepo, targetTag)
					continue
				}

				fmt.Printf("Deleting: %s:%s\n", targetRepo, targetTag)
				
				var deleteErr error
				if s.cleanupConfig.DeleteManifests {
					manifest, err := s.targetClient.GetManifest(ctx, targetRepo, targetTag)
					if err == nil {
						deleteErr = s.targetClient.DeleteManifest(ctx, targetRepo, manifest.Digest)
					}
				} else if s.cleanupConfig.DeleteTags {
					deleteErr = s.targetClient.DeleteTag(ctx, targetRepo, targetTag)
				}

				if s.auditLogger != nil {
					digest := ""
					if manifest, err := s.targetClient.GetManifest(ctx, targetRepo, targetTag); err == nil {
						digest = manifest.Digest
					}
					s.auditLogger.LogDelete(targetRepo, targetTag, digest, deleteErr)
				}

				if deleteErr != nil {
					fmt.Printf("Failed to delete %s:%s: %v\n", targetRepo, targetTag, deleteErr)
				} else {
					fmt.Printf("Successfully deleted: %s:%s\n", targetRepo, targetTag)
				}
			}
		}
	}

	fmt.Println("Cleanup completed.")
	return nil
}

func (s *ImageSyncer) mapRepository(sourceRepo string) string {
	targetRepo := sourceRepo
	if s.sourcePrefix != "" {
		targetRepo = strings.TrimPrefix(targetRepo, s.sourcePrefix)
		targetRepo = strings.TrimPrefix(targetRepo, "/")
	}
	if s.targetPrefix != "" {
		targetRepo = s.targetPrefix + "/" + targetRepo
	}
	return targetRepo
}

func (s *ImageSyncer) Close() {
	if s.rateLimiter != nil {
		s.rateLimiter.Stop()
	}
	if s.auditLogger != nil {
		s.auditLogger.Close()
	}
}

type SyncStatistics struct {
	TotalImages      int
	CompletedImages  int
	FailedImages     int
	SkippedImages    int
	TotalBytes       int64
	TransferredBytes int64
	ElapsedTime      time.Duration
	CurrentRate      int64
}

func (s *ImageSyncer) GetStatistics() *SyncStatistics {
	total, completed, failed, skipped := s.progress.GetStats()
	totalBytes, transferredBytes := s.progress.GetBytes()

	var currentRate int64
	if s.rateLimiter != nil {
		currentRate = s.rateLimiter.GetCurrentRate()
	}

	return &SyncStatistics{
		TotalImages:      int(total),
		CompletedImages:  int(completed),
		FailedImages:     int(failed),
		SkippedImages:    int(skipped),
		TotalBytes:       totalBytes,
		TransferredBytes: transferredBytes,
		ElapsedTime:      s.progress.ElapsedTime(),
		CurrentRate:      currentRate,
	}
}

func (stat *SyncStatistics) String() string {
	speed := float64(stat.TransferredBytes) / stat.ElapsedTime.Seconds()
	return fmt.Sprintf(
		"Sync Statistics:\n"+
			"  Total Images:     %d\n"+
			"  Completed:        %d\n"+
			"  Failed:           %d\n"+
			"  Skipped:          %d\n"+
			"  Transferred:      %s\n"+
			"  Elapsed Time:     %v\n"+
			"  Current Rate:     %s/s\n"+
			"  Avg Speed:        %s/s",
		stat.TotalImages,
		stat.CompletedImages,
		stat.FailedImages,
		stat.SkippedImages,
		formatBytes(stat.TransferredBytes),
		stat.ElapsedTime.Truncate(time.Second),
		formatBytes(stat.CurrentRate),
		formatBytes(int64(speed)),
	)
}

func formatBytes(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.2f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

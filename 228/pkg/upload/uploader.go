package upload

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/client"
	"github.com/opencontainers/go-digest"
	"golang.org/x/sync/errgroup"
)

type UploadStatus string

const (
	StatusPending    UploadStatus = "pending"
	StatusUploading  UploadStatus = "uploading"
	StatusComplete   UploadStatus = "complete"
	StatusFailed     UploadStatus = "failed"
	StatusSkipped    UploadStatus = "skipped"
)

type ChunkUpload struct {
	Index        int
	StartOffset  int64
	EndOffset    int64
	Size         int64
	Uploaded     bool
	UploadedAt   time.Time
	UploadURL    string
}

type UploadProgress struct {
	LayerDigest   string         `json:"layer_digest"`
	UploadUUID    string         `json:"upload_uuid"`
	TotalSize     int64          `json:"total_size"`
	UploadedSize  int64          `json:"uploaded_size"`
	ChunkSize     int64          `json:"chunk_size"`
	Chunks        []*ChunkUpload `json:"chunks"`
	UploadURL     string         `json:"upload_url"`
	LastUpdated   time.Time      `json:"last_updated"`
	Completed     bool           `json:"completed"`
}

type UploadProgressDB struct {
	Progresses map[string]*UploadProgress `json:"progresses"`
}

type LayerUpload struct {
	Digest          digest.Digest
	SizeBytes       int64
	Status          UploadStatus
	ProgressBytes   int64
	StartTime       time.Time
	EndTime         time.Time
	Error           error
	Retries         int
	AlreadyExists   bool
	Progress        *UploadProgress
	ChunkSize       int64
}

type UploadConfig struct {
	RegistryURL      string
	Username         string
	Password         string
	Concurrency      int
	MaxRetries       int
	RetryDelay       time.Duration
	Insecure         bool
	ChunkSize        int64
	ProgressFile     string
	EnableResumable  bool
}

type ParallelUploader struct {
	cli             *client.Client
	config          *UploadConfig
	layers          map[digest.Digest]*LayerUpload
	progressChan    chan *LayerUpload
	progressDB      *UploadProgressDB
	mu              sync.Mutex
}

func NewParallelUploader(cli *client.Client, config *UploadConfig) (*ParallelUploader, error) {
	if config.ChunkSize == 0 {
		config.ChunkSize = 8 * 1024 * 1024
	}
	if config.ProgressFile == "" {
		config.ProgressFile = ".upload-progress.json"
	}

	progressDB, err := loadProgressDB(config.ProgressFile)
	if err != nil {
		return nil, fmt.Errorf("failed to load progress DB: %w", err)
	}

	return &ParallelUploader{
		cli:          cli,
		config:       config,
		layers:       make(map[digest.Digest]*LayerUpload),
		progressChan: make(chan *LayerUpload, 100),
		progressDB:   progressDB,
	}, nil
}

func loadProgressDB(path string) (*UploadProgressDB, error) {
	db := &UploadProgressDB{
		Progresses: make(map[string]*UploadProgress),
	}

	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return db, nil
		}
		return nil, err
	}

	if err := json.Unmarshal(data, db); err != nil {
		return db, nil
	}

	return db, nil
}

func (pu *ParallelUploader) SaveProgressDB() error {
	pu.mu.Lock()
	defer pu.mu.Unlock()

	data, err := json.MarshalIndent(pu.progressDB, "", "  ")
	if err != nil {
		return err
	}

	dir := filepath.Dir(pu.config.ProgressFile)
	if dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return err
		}
	}

	return os.WriteFile(pu.config.ProgressFile, data, 0644)
}

func (pu *ParallelUploader) GetSavedProgress(layerDigest string) (*UploadProgress, bool) {
	pu.mu.Lock()
	defer pu.mu.Unlock()

	progress, exists := pu.progressDB.Progresses[layerDigest]
	if exists && !progress.Completed {
		return progress, true
	}
	return nil, false
}

func (pu *ParallelUploader) UpdateProgress(progress *UploadProgress) {
	pu.mu.Lock()
	defer pu.mu.Unlock()

	progress.LastUpdated = time.Now()
	pu.progressDB.Progresses[progress.LayerDigest] = progress
}

func (pu *ParallelUploader) UploadImage(ctx context.Context, imageName, tag string) error {
	imageRef := fmt.Sprintf("%s/%s:%s", pu.config.RegistryURL, imageName, tag)

	inspect, _, err := pu.cli.ImageInspectWithRaw(ctx, fmt.Sprintf("%s:%s", imageName, tag))
	if err != nil {
		return fmt.Errorf("failed to inspect image: %w", err)
	}

	for _, layer := range inspect.RootFS.Layers {
		d, err := digest.Parse(layer)
		if err != nil {
			continue
		}
		pu.layers[d] = &LayerUpload{
			Digest: d,
			Status: StatusPending,
		}
	}

	return pu.uploadLayers(ctx)
}

func (pu *ParallelUploader) uploadLayers(ctx context.Context) error {
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(pu.config.Concurrency)

	for _, layer := range pu.layers {
		layer := layer
		g.Go(func() error {
			return pu.uploadLayerWithRetry(ctx, layer)
		})
	}

	return g.Wait()
}

func (pu *ParallelUploader) uploadLayerWithRetry(ctx context.Context, layer *LayerUpload) error {
	var lastErr error

	for retry := 0; retry <= pu.config.MaxRetries; retry++ {
		if err := pu.uploadLayer(ctx, layer); err != nil {
			lastErr = err
			layer.Retries = retry + 1
			time.Sleep(pu.config.RetryDelay)
			continue
		}
		return nil
	}

	pu.mu.Lock()
	layer.Status = StatusFailed
	layer.Error = lastErr
	pu.mu.Unlock()

	pu.sendProgress(layer)
	return lastErr
}

func (pu *ParallelUploader) uploadLayer(ctx context.Context, layer *LayerUpload) error {
	pu.mu.Lock()
	layer.Status = StatusUploading
	layer.StartTime = time.Now()
	pu.mu.Unlock()

	pu.sendProgress(layer)

	exists, err := pu.checkLayerExists(ctx, layer.Digest)
	if err != nil {
		return err
	}

	if exists {
		pu.mu.Lock()
		layer.Status = StatusComplete
		layer.AlreadyExists = true
		layer.EndTime = time.Now()
		pu.mu.Unlock()
		pu.sendProgress(layer)
		return nil
	}

	if pu.config.EnableResumable {
		err = pu.pushLayerResumable(ctx, layer)
	} else {
		err = pu.pushLayer(ctx, layer)
	}
	
	if err != nil {
		return err
	}

	pu.mu.Lock()
	layer.Status = StatusComplete
	layer.EndTime = time.Now()
	pu.mu.Unlock()

	pu.sendProgress(layer)
	return nil
}

func (pu *ParallelUploader) pushLayerResumable(ctx context.Context, layer *LayerUpload) error {
	var uploadProgress *UploadProgress
	var exists bool

	if pu.config.EnableResumable {
		uploadProgress, exists = pu.GetSavedProgress(layer.Digest.String())
	}

	if !exists {
		uploadURL, err := pu.initiateUpload(ctx)
		if err != nil {
			return err
		}

		uploadProgress = &UploadProgress{
			LayerDigest: layer.Digest.String(),
			UploadURL:   uploadURL,
			TotalSize:   layer.SizeBytes,
			ChunkSize:   pu.config.ChunkSize,
			Chunks:      make([]*ChunkUpload, 0),
		}

		numChunks := (layer.SizeBytes + pu.config.ChunkSize - 1) / pu.config.ChunkSize
		for i := int64(0); i < numChunks; i++ {
			start := i * pu.config.ChunkSize
			end := (i + 1) * pu.config.ChunkSize
			if end > layer.SizeBytes {
				end = layer.SizeBytes
			}
			uploadProgress.Chunks = append(uploadProgress.Chunks, &ChunkUpload{
				Index:       int(i),
				StartOffset: start,
				EndOffset:   end,
				Size:        end - start,
				Uploaded:    false,
			})
		}

		pu.UpdateProgress(uploadProgress)
		pu.SaveProgressDB()
	} else {
		fmt.Printf("[%s] Resuming upload from saved progress, %.1f%% complete\n",
			shortDigest(layer.Digest.String()),
			float64(uploadProgress.UploadedSize)/float64(uploadProgress.TotalSize)*100)
	}

	layer.Progress = uploadProgress

	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(pu.config.Concurrency)

	for _, chunk := range uploadProgress.Chunks {
		if chunk.Uploaded {
			continue
		}
		chunk := chunk
		g.Go(func() error {
			return pu.uploadChunk(ctx, layer, chunk, uploadProgress)
		})
	}

	if err := g.Wait(); err != nil {
		return err
	}

	return pu.finalizeUpload(ctx, layer, uploadProgress)
}

func (pu *ParallelUploader) initiateUpload(ctx context.Context) (string, error) {
	uploadURL := fmt.Sprintf("%s/v2/library/image/blobs/uploads/", pu.config.RegistryURL)
	req, err := http.NewRequestWithContext(ctx, "POST", uploadURL, nil)
	if err != nil {
		return "", err
	}

	if pu.config.Username != "" {
		req.SetBasicAuth(pu.config.Username, pu.config.Password)
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	location := resp.Header.Get("Location")
	if location == "" {
		return "", fmt.Errorf("no upload location received")
	}

	if !strings.HasPrefix(location, "http") {
		location = pu.config.RegistryURL + location
	}

	return location, nil
}

func (pu *ParallelUploader) uploadChunk(ctx context.Context, layer *LayerUpload, chunk *ChunkUpload, progress *UploadProgress) error {
	reader, err := pu.cli.ImageSave(ctx, []string{layer.Digest.String()})
	if err != nil {
		return err
	}
	defer reader.Close()

	_, err = io.CopyN(io.Discard, reader, chunk.StartOffset)
	if err != nil {
		return err
	}

	chunkReader := io.LimitReader(reader, chunk.Size)

	patchURL := fmt.Sprintf("%s&offset=%d", progress.UploadURL, chunk.StartOffset)
	patchReq, err := http.NewRequestWithContext(ctx, "PATCH", patchURL, chunkReader)
	if err != nil {
		return err
	}

	patchReq.Header.Set("Content-Type", "application/octet-stream")
	patchReq.Header.Set("Content-Range", fmt.Sprintf("%d-%d", chunk.StartOffset, chunk.EndOffset-1))
	patchReq.ContentLength = chunk.Size

	if pu.config.Username != "" {
		patchReq.SetBasicAuth(pu.config.Username, pu.config.Password)
	}

	client := &http.Client{Timeout: 5 * time.Minute}
	resp, err := client.Do(patchReq)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("chunk upload failed (status %d): %s", resp.StatusCode, body)
	}

	pu.mu.Lock()
	chunk.Uploaded = true
	chunk.UploadedAt = time.Now()
	progress.UploadedSize += chunk.Size
	pu.mu.Unlock()

	pu.UpdateProgress(progress)
	pu.SaveProgressDB()

	pu.mu.Lock()
	layer.ProgressBytes = progress.UploadedSize
	pu.mu.Unlock()
	pu.sendProgress(layer)

	return nil
}

func (pu *ParallelUploader) finalizeUpload(ctx context.Context, layer *LayerUpload, progress *UploadProgress) error {
	putURL := fmt.Sprintf("%s&digest=%s", progress.UploadURL, layer.Digest)
	putReq, err := http.NewRequestWithContext(ctx, "PUT", putURL, nil)
	if err != nil {
		return err
	}

	putReq.Header.Set("Content-Type", "application/octet-stream")

	if pu.config.Username != "" {
		putReq.SetBasicAuth(pu.config.Username, pu.config.Password)
	}

	client := &http.Client{Timeout: 2 * time.Minute}
	resp, err := client.Do(putReq)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("finalize upload failed: %s - %s", resp.Status, body)
	}

	progress.Completed = true
	pu.UpdateProgress(progress)
	pu.SaveProgressDB()

	return nil
}

func (pu *ParallelUploader) checkLayerExists(ctx context.Context, d digest.Digest) (bool, error) {
	url := fmt.Sprintf("%s/v2/library/image/blobs/%s", pu.config.RegistryURL, d)
	
	req, err := http.NewRequestWithContext(ctx, "HEAD", url, nil)
	if err != nil {
		return false, err
	}

	if pu.config.Username != "" {
		req.SetBasicAuth(pu.config.Username, pu.config.Password)
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return false, nil
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK, nil
}

func (pu *ParallelUploader) pushLayer(ctx context.Context, layer *LayerUpload) error {
	reader, err := pu.cli.ImageSave(ctx, []string{layer.Digest.String()})
	if err != nil {
		return err
	}
	defer reader.Close()

	uploadURL := fmt.Sprintf("%s/v2/library/image/blobs/uploads/", pu.config.RegistryURL)
	req, err := http.NewRequestWithContext(ctx, "POST", uploadURL, nil)
	if err != nil {
		return err
	}

	if pu.config.Username != "" {
		req.SetBasicAuth(pu.config.Username, pu.config.Password)
	}

	client := &http.Client{Timeout: 5 * time.Minute}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	location := resp.Header.Get("Location")
	if location == "" {
		return fmt.Errorf("no upload location received")
	}

	if !strings.HasPrefix(location, "http") {
		location = pu.config.RegistryURL + location
	}

	putURL := fmt.Sprintf("%s&digest=%s", location, layer.Digest)
	putReq, err := http.NewRequestWithContext(ctx, "PUT", putURL, reader)
	if err != nil {
		return err
	}
	putReq.Header.Set("Content-Type", "application/octet-stream")

	if pu.config.Username != "" {
		putReq.SetBasicAuth(pu.config.Username, pu.config.Password)
	}

	putResp, err := client.Do(putReq)
	if err != nil {
		return err
	}
	defer putResp.Body.Close()

	if putResp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(putResp.Body)
		return fmt.Errorf("upload failed: %s - %s", putResp.Status, body)
	}

	return nil
}

func (pu *ParallelUploader) sendProgress(layer *LayerUpload) {
	select {
	case pu.progressChan <- layer:
	default:
	}
}

func (pu *ParallelUploader) ProgressChannel() <-chan *LayerUpload {
	return pu.progressChan
}

func (pu *ParallelUploader) Close() {
	close(pu.progressChan)
}

func (pu *ParallelUploader) GetStats() (total, completed, uploading, skipped, failed int, totalSize, uploadedSize int64) {
	pu.mu.Lock()
	defer pu.mu.Unlock()

	total = len(pu.layers)
	for _, layer := range pu.layers {
		switch layer.Status {
		case StatusComplete:
			completed++
			if layer.AlreadyExists {
				skipped++
			}
			totalSize += layer.SizeBytes
			uploadedSize += layer.SizeBytes
		case StatusUploading:
			uploading++
			totalSize += layer.SizeBytes
			uploadedSize += layer.ProgressBytes
		case StatusFailed:
			failed++
			totalSize += layer.SizeBytes
		case StatusPending:
			totalSize += layer.SizeBytes
		}
	}

	return total, completed, uploading, skipped, failed, totalSize, uploadedSize
}

func (pu *ParallelUploader) PrintSummary() {
	fmt.Println("\n=== Parallel Upload Summary ===")
	
	total, completed, uploading, skipped, failed, totalSize, _ := pu.GetStats()
	
	fmt.Printf("Total Layers: %d\n", total)
	fmt.Printf("Completed: %d (%d already exist)\n", completed, skipped)
	fmt.Printf("Uploading: %d\n", uploading)
	fmt.Printf("Failed: %d\n", failed)
	fmt.Printf("Total Size: %.2f MB\n", float64(totalSize)/1024/1024)

	var totalDuration time.Duration
	var maxEnd time.Time
	var minStart time.Time = time.Now()

	for _, layer := range pu.layers {
		if !layer.StartTime.IsZero() {
			duration := layer.EndTime.Sub(layer.StartTime)
			totalDuration += duration
			
			if layer.StartTime.Before(minStart) {
				minStart = layer.StartTime
			}
			if layer.EndTime.After(maxEnd) {
				maxEnd = layer.EndTime
			}
		}
	}

	wallTime := maxEnd.Sub(minStart)
	fmt.Printf("\nTotal Upload Time: %.2fs (wall clock)\n", wallTime.Seconds())
	
	if wallTime > 0 {
		fmt.Printf("Effective Throughput: %.2f MB/s\n", 
			float64(totalSize)/1024/1024/wallTime.Seconds())
	}

	fmt.Println("\nLayer Details:")
	for d, layer := range pu.layers {
		statusIcon := "✓"
		if layer.Status == StatusFailed {
			statusIcon = "✗"
		} else if layer.AlreadyExists {
			statusIcon = "⊘"
		}
		
		duration := layer.EndTime.Sub(layer.StartTime)
		fmt.Printf("  %s %s: %s (%.2fs)\n", 
			statusIcon, 
			shortDigest(d.String()), 
			layer.Status, 
			duration.Seconds())
	}
}

func shortDigest(d string) string {
	if len(d) > 19 {
		return d[:18] + "..."
	}
	return d
}

func (pu *ParallelUploader) SaveImageWithProgress(ctx context.Context, imageRef string) (io.ReadCloser, <-chan int64, error) {
	progressChan := make(chan int64, 100)
	
	reader, err := pu.cli.ImageSave(ctx, []string{imageRef})
	if err != nil {
		close(progressChan)
		return nil, nil, err
	}

	pr, pw := io.Pipe()
	
	go func() {
		defer pw.Close()
		defer close(progressChan)
		
		buf := make([]byte, 32*1024)
		var total int64
		
		for {
			n, err := reader.Read(buf)
			if n > 0 {
				if _, werr := pw.Write(buf[:n]); werr != nil {
					return
				}
				total += int64(n)
				select {
				case progressChan <- total:
				default:
				}
			}
			if err == io.EOF {
				return
			}
			if err != nil {
				return
			}
		}
	}()

	return pr, progressChan, nil
}

func DefaultUploadConfig(registryURL string) *UploadConfig {
	return &UploadConfig{
		RegistryURL:     registryURL,
		Concurrency:     4,
		MaxRetries:      3,
		RetryDelay:      2 * time.Second,
		Insecure:        false,
		ChunkSize:       8 * 1024 * 1024,
		ProgressFile:    ".upload-progress.json",
		EnableResumable: true,
	}
}

type PushResponse struct {
	Status     string
	ProgressDetail *types.ProgressDetail
	Id         string
}

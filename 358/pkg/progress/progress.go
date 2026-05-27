package progress

import (
	"sync"
	"sync/atomic"
	"time"
)

type SyncStatus string

const (
	StatusPending   SyncStatus = "pending"
	StatusRunning   SyncStatus = "running"
	StatusCompleted SyncStatus = "completed"
	StatusFailed    SyncStatus = "failed"
	StatusSkipped   SyncStatus = "skipped"
)

type ImageProgress struct {
	SourceRepo   string
	SourceTag    string
	TargetRepo   string
	TargetTag    string
	Status       SyncStatus
	TotalBytes   int64
	CurrentBytes int64
	StartTime    time.Time
	EndTime      time.Time
	Error        error
}

type SyncProgress struct {
	mu              sync.RWMutex
	TotalImages     int32
	CompletedImages int32
	FailedImages    int32
	SkippedImages   int32
	TotalBytes       int64
	TransferredBytes int64
	Images          map[string]*ImageProgress
	StartTime        time.Time
	EndTime          time.Time
}

func NewSyncProgress() *SyncProgress {
	return &SyncProgress{
		Images: make(map[string]*ImageProgress),
	}
}

func (p *SyncProgress) AddImage(sourceRepo, sourceTag, targetRepo, targetTag string) {
	p.mu.Lock()
	defer p.mu.Unlock()

	key := sourceRepo + ":" + sourceTag
	p.Images[key] = &ImageProgress{
		SourceRepo: sourceRepo,
		SourceTag:  sourceTag,
		TargetRepo:   targetRepo,
		TargetTag:    targetTag,
		Status:       StatusPending,
	}
	atomic.AddInt32(&p.TotalImages, 1)
}

func (p *SyncProgress) StartImage(sourceRepo, sourceTag string, totalBytes int64) {
	p.mu.Lock()
	defer p.mu.Unlock()

	key := sourceRepo + ":" + sourceTag
	if img, ok := p.Images[key]; ok {
		img.Status = StatusRunning
		img.TotalBytes = totalBytes
		img.StartTime = time.Now()
	}
}

func (p *SyncProgress) UpdateProgress(sourceRepo, sourceTag string, bytes int64) {
	key := sourceRepo + ":" + sourceTag
	
	p.mu.RLock()
	img, ok := p.Images[key]
	p.mu.RUnlock()
	
	if ok {
		atomic.AddInt64(&img.CurrentBytes, bytes)
		atomic.AddInt64(&p.TransferredBytes, bytes)
	}
}

func (p *SyncProgress) CompleteImage(sourceRepo, sourceTag string) {
	p.mu.Lock()
	defer p.mu.Unlock()

	key := sourceRepo + ":" + sourceTag
	if img, ok := p.Images[key]; ok {
		img.Status = StatusCompleted
		img.EndTime = time.Now()
	}
	atomic.AddInt32(&p.CompletedImages, 1)
}

func (p *SyncProgress) FailImage(sourceRepo, sourceTag string, err error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	key := sourceRepo + ":" + sourceTag
	if img, ok := p.Images[key]; ok {
		img.Status = StatusFailed
		img.EndTime = time.Now()
		img.Error = err
	}
	atomic.AddInt32(&p.FailedImages, 1)
}

func (p *SyncProgress) SkipImage(sourceRepo, sourceTag string) {
	p.mu.Lock()
	defer p.mu.Unlock()

	key := sourceRepo + ":" + sourceTag
	if img, ok := p.Images[key]; ok {
		img.Status = StatusSkipped
		img.EndTime = time.Now()
	}
	atomic.AddInt32(&p.SkippedImages, 1)
}

func (p *SyncProgress) Start() {
	p.StartTime = time.Now()
}

func (p *SyncProgress) Finish() {
	p.EndTime = time.Now()
}

func (p *SyncProgress) GetStats() (total, completed, failed, skipped int32) {
	return atomic.LoadInt32(&p.TotalImages),
		atomic.LoadInt32(&p.CompletedImages),
		atomic.LoadInt32(&p.FailedImages),
		atomic.LoadInt32(&p.SkippedImages)
}

func (p *SyncProgress) GetBytes() (total, transferred int64) {
	return atomic.LoadInt64(&p.TotalBytes),
		atomic.LoadInt64(&p.TransferredBytes)
}

func (p *SyncProgress) GetImageProgress(sourceRepo, sourceTag string) *ImageProgress {
	p.mu.RLock()
	defer p.mu.RUnlock()

	key := sourceRepo + ":" + sourceTag
	return p.Images[key]
}

func (p *SyncProgress) GetAllImages() []*ImageProgress {
	p.mu.RLock()
	defer p.mu.RUnlock()

	images := make([]*ImageProgress, 0, len(p.Images))
	for _, img := range p.Images {
		images = append(images, img)
	}
	return images
}

func (p *SyncProgress) ElapsedTime() time.Duration {
	if p.EndTime.IsZero() {
		return time.Since(p.StartTime)
	}
	return p.EndTime.Sub(p.StartTime)
}

type ProgressWriter struct {
	writer      interface{}
	progress     *SyncProgress
	sourceRepo   string
	sourceTag    string
	written      int64
}

func NewProgressWriter(progress *SyncProgress, sourceRepo, sourceTag string) *ProgressWriter {
	return &ProgressWriter{
		progress:   progress,
		sourceRepo: sourceRepo,
		sourceTag:  sourceTag,
	}
}

func (pw *ProgressWriter) Write(p []byte) (n int, err error) {
	n = len(p)
	pw.progress.UpdateProgress(pw.sourceRepo, pw.sourceTag, int64(n))
	pw.written += int64(n)
	return n, nil
}

func (pw *ProgressWriter) Written() int64 {
	return pw.written
}

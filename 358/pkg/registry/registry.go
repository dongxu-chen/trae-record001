package registry

import (
	"context"
	"io"
	"sync"
	"sync/atomic"
	"time"
)

type ImageInfo struct {
	Repository string
	Tag        string
	Digest     string
	Size       int64
	CreatedAt  time.Time
	MediaType  string
}

type Manifest struct {
	Content       []byte
	Digest        string
	MediaType     string
	SchemaVersion int
}

type Layer struct {
	Digest    string
	Size      int64
	MediaType string
	Blob      io.ReadCloser
}

type RegistryClient interface {
	ListRepositories(ctx context.Context, prefix string) ([]string, error)
	ListTags(ctx context.Context, repository string) ([]string, error)
	GetImageInfo(ctx context.Context, repository, tag string) (*ImageInfo, error)
	GetManifest(ctx context.Context, repository, reference string) (*Manifest, error)
	GetBlob(ctx context.Context, repository, digest string) (io.ReadCloser, int64, error)
	PushManifest(ctx context.Context, repository, reference string, manifest *Manifest) error
	PushBlob(ctx context.Context, repository, digest string, content io.Reader, size int64) error
	DeleteTag(ctx context.Context, repository, tag string) error
	DeleteManifest(ctx context.Context, repository, reference string) error
	BlobExists(ctx context.Context, repository, digest string) (bool, error)
	ManifestExists(ctx context.Context, repository, reference string) (bool, error)
}

type RateLimitedReader struct {
	reader      io.Reader
	rateLimiter *DynamicRateLimiter
}

func NewRateLimitedReader(reader io.Reader, rateLimiter *DynamicRateLimiter) *RateLimitedReader {
	return &RateLimitedReader{
		reader:      reader,
		rateLimiter: rateLimiter,
	}
}

func (r *RateLimitedReader) Read(p []byte) (n int, err error) {
	n, err = r.reader.Read(p)
	if n > 0 && r.rateLimiter != nil {
		r.rateLimiter.WaitN(n)
	}
	return n, err
}

func (r *RateLimitedReader) Close() error {
	if closer, ok := r.reader.(io.Closer); ok {
		return closer.Close()
	}
	return nil
}

type DynamicRateLimiter struct {
	mu              sync.RWMutex
	currentRate     int64
	maxRate         int64
	minRate         int64
	ticker          *time.Ticker
	bucket          int64
	maxBucket       int64
	latencyHistory  []time.Duration
	latencyIndex    int
	latencyCount    int
	transferStats   struct {
		bytesTransferred int64
		startTime        time.Time
	}
	adjustmentInterval time.Duration
	lastAdjustment     time.Time
	stopped            int32
}

func NewDynamicRateLimiter(initialRate int64, maxRate int64, minRate int64) *DynamicRateLimiter {
	if initialRate <= 0 {
		return nil
	}
	if maxRate <= 0 {
		maxRate = initialRate * 4
	}
	if minRate <= 0 {
		minRate = initialRate / 4
	}

	rl := &DynamicRateLimiter{
		currentRate:        initialRate,
		maxRate:            maxRate,
		minRate:            minRate,
		ticker:             time.NewTicker(time.Second / 10),
		bucket:             initialRate / 10,
		maxBucket:          initialRate,
		latencyHistory:     make([]time.Duration, 10),
		adjustmentInterval: 5 * time.Second,
		lastAdjustment:     time.Now(),
	}
	rl.transferStats.startTime = time.Now()
	go rl.refill()
	go rl.adjustRate()
	return rl
}

func (rl *DynamicRateLimiter) refill() {
	for {
		if atomic.LoadInt32(&rl.stopped) == 1 {
			return
		}
		<-rl.ticker.C
		rl.mu.Lock()
		newBucket := rl.bucket + rl.currentRate/10
		if newBucket > rl.maxBucket {
			rl.bucket = rl.maxBucket
		} else {
			rl.bucket = newBucket
		}
		rl.mu.Unlock()
	}
}

func (rl *DynamicRateLimiter) adjustRate() {
	for {
		if atomic.LoadInt32(&rl.stopped) == 1 {
			return
		}
		time.Sleep(rl.adjustmentInterval)

		rl.mu.Lock()
		now := time.Now()

		if rl.latencyCount > 0 {
			var totalLatency time.Duration
			count := rl.latencyCount
			if count > len(rl.latencyHistory) {
				count = len(rl.latencyHistory)
			}
			for i := 0; i < count; i++ {
				totalLatency += rl.latencyHistory[i]
			}
			avgLatency := totalLatency / time.Duration(count)

			elapsed := now.Sub(rl.transferStats.startTime).Seconds()
			if elapsed > 0 {
				actualRate := int64(float64(rl.transferStats.bytesTransferred) / elapsed)

				if avgLatency > 500*time.Millisecond && rl.currentRate > rl.minRate {
					rl.currentRate = rl.currentRate * 8 / 10
					if rl.currentRate < rl.minRate {
						rl.currentRate = rl.minRate
					}
				} else if avgLatency < 100*time.Millisecond && actualRate >= rl.currentRate*8/10 && rl.currentRate < rl.maxRate {
					rl.currentRate = rl.currentRate * 11 / 10
					if rl.currentRate > rl.maxRate {
						rl.currentRate = rl.maxRate
					}
				}
				rl.maxBucket = rl.currentRate
			}
		}

		rl.transferStats.bytesTransferred = 0
		rl.transferStats.startTime = now
		rl.latencyCount = 0
		rl.lastAdjustment = now

		rl.mu.Unlock()
	}
}

func (rl *DynamicRateLimiter) RecordLatency(latency time.Duration) {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	rl.latencyHistory[rl.latencyIndex] = latency
	rl.latencyIndex = (rl.latencyIndex + 1) % len(rl.latencyHistory)
	if rl.latencyCount < len(rl.latencyHistory) {
		rl.latencyCount++
	}
}

func (rl *DynamicRateLimiter) RecordTransfer(bytes int64) {
	rl.mu.Lock()
	defer rl.mu.Unlock()
	rl.transferStats.bytesTransferred += bytes
}

func (rl *DynamicRateLimiter) WaitN(n int) {
	if rl == nil {
		return
	}
	needed := int64(n)
	for needed > 0 {
		rl.mu.Lock()
		if rl.bucket >= needed {
			rl.bucket -= needed
			rl.mu.Unlock()
			needed = 0
		} else {
			consumed := rl.bucket
			rl.bucket = 0
			rl.mu.Unlock()
			needed -= consumed
			time.Sleep(time.Second / 10)
		}
	}
}

func (rl *DynamicRateLimiter) GetCurrentRate() int64 {
	rl.mu.RLock()
	defer rl.mu.RUnlock()
	return rl.currentRate
}

func (rl *DynamicRateLimiter) SetRate(rate int64) {
	rl.mu.Lock()
	defer rl.mu.Unlock()
	if rate >= rl.minRate && rate <= rl.maxRate {
		rl.currentRate = rate
		rl.maxBucket = rate
	}
}

func (rl *DynamicRateLimiter) Stop() {
	if rl != nil && rl.ticker != nil {
		atomic.StoreInt32(&rl.stopped, 1)
		rl.ticker.Stop()
	}
}

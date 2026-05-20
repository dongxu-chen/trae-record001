package backup

import (
	"bytes"
	"compress/gzip"
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"io"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"

	"backup-tool/pkg/config"
	"backup-tool/pkg/logger"
	"github.com/google/uuid"
)

type Pipeline struct {
	cfg         *config.BackupConfig
	encryptKey  []byte
	stats       PipelineStats
	jobChan     chan *PipelineJob
	compressChan chan *PipelineJob
	encryptChan  chan *PipelineJob
	uploadChan   chan *PipelineJob
	resultChan   chan *PipelineJob
	wg           sync.WaitGroup
}

func NewPipeline(cfg *config.BackupConfig) *Pipeline {
	return &Pipeline{
		cfg:         cfg,
		encryptKey:  []byte(cfg.EncryptionKey),
		jobChan:     make(chan *PipelineJob, cfg.PipelineSize),
		compressChan: make(chan *PipelineJob, cfg.PipelineSize),
		encryptChan: make(chan *PipelineJob, cfg.PipelineSize),
		uploadChan:  make(chan *PipelineJob, cfg.PipelineSize),
		resultChan:  make(chan *PipelineJob, cfg.PipelineSize),
	}
}

func (p *Pipeline) Start(ctx context.Context, uploader Uploader) {
	logger.Info("Starting backup pipeline")

	for i := 0; i < p.cfg.ParallelWorkers; i++ {
		p.wg.Add(1)
		go p.compressWorker(ctx)
	}

	for i := 0; i < p.cfg.ParallelWorkers; i++ {
		p.wg.Add(1)
		go p.encryptWorker(ctx)
	}

	for i := 0; i < p.cfg.ParallelWorkers; i++ {
		p.wg.Add(1)
		go p.uploadWorker(ctx, uploader)
	}

	go p.collectResults(ctx)
}

func (p *Pipeline) Submit(job *PipelineJob) {
	atomic.AddInt64(&p.stats.TotalJobs, 1)
	atomic.AddInt64(&p.stats.BackupJobs, 1)
	job.ID = uuid.New().String()
	job.SetStage(StageBackup)
	p.compressChan <- job
}

func (p *Pipeline) compressWorker(ctx context.Context) {
	defer p.wg.Done()

	for {
		select {
		case <-ctx.Done():
			return
		case job := <-p.compressChan:
			if job == nil {
				return
			}

			if !p.cfg.Compress {
				job.SetStage(StageCompress)
				atomic.AddInt64(&p.stats.CompressJobs, 1)
				p.encryptChan <- job
				continue
			}

			logger.Infof("Compressing: %s", job.FilePath)
			job.SetStage(StageCompress)

			compressedPath, err := p.compressFile(job.FilePath)
			if err != nil {
				job.SetError(err)
				logger.Errorf("Compress failed for %s: %v", job.FilePath, err)
				p.resultChan <- job
				continue
			}

			job.FilePath = compressedPath
			if job.BackupResult != nil {
				job.BackupResult.FilePath = compressedPath
			}

			atomic.AddInt64(&p.stats.CompressJobs, 1)
			logger.Infof("Compress completed: %s", compressedPath)
			p.encryptChan <- job
		}
	}
}

func (p *Pipeline) compressFile(filePath string) (string, error) {
	input, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer input.Close()

	compressedPath := filePath + ".gz"
	output, err := os.Create(compressedPath)
	if err != nil {
		return "", err
	}
	defer output.Close()

	gzipWriter := gzip.NewWriter(output)
	defer gzipWriter.Close()

	if _, err := io.Copy(gzipWriter, input); err != nil {
		return "", err
	}

	os.Remove(filePath)
	return compressedPath, nil
}

func (p *Pipeline) encryptWorker(ctx context.Context) {
	defer p.wg.Done()

	for {
		select {
		case <-ctx.Done():
			return
		case job := <-p.encryptChan:
			if job == nil {
				return
			}

			if !p.cfg.Encrypt {
				job.SetStage(StageEncrypt)
				atomic.AddInt64(&p.stats.EncryptJobs, 1)
				p.uploadChan <- job
				continue
			}

			logger.Infof("Encrypting: %s", job.FilePath)
			job.SetStage(StageEncrypt)

			encryptedPath, err := p.encryptFile(job.FilePath)
			if err != nil {
				job.SetError(err)
				logger.Errorf("Encrypt failed for %s: %v", job.FilePath, err)
				p.resultChan <- job
				continue
			}

			job.FilePath = encryptedPath
			if job.BackupResult != nil {
				job.BackupResult.FilePath = encryptedPath
			}

			atomic.AddInt64(&p.stats.EncryptJobs, 1)
			logger.Infof("Encrypt completed: %s", encryptedPath)
			p.uploadChan <- job
		}
	}
}

func (p *Pipeline) encryptFile(filePath string) (string, error) {
	input, err := os.ReadFile(filePath)
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(p.encryptKey)
	if err != nil {
		return "", err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}

	ciphertext := gcm.Seal(nonce, nonce, input, nil)

	encryptedPath := filePath + ".aes"
	if err := os.WriteFile(encryptedPath, ciphertext, 0644); err != nil {
		return "", err
	}

	os.Remove(filePath)
	return encryptedPath, nil
}

func (p *Pipeline) uploadWorker(ctx context.Context, uploader Uploader) {
	defer p.wg.Done()

	for {
		select {
		case <-ctx.Done():
			return
		case job := <-p.uploadChan:
			if job == nil {
				return
			}

			if uploader == nil {
				job.SetStage(StageUpload)
				atomic.AddInt64(&p.stats.UploadJobs, 1)
				atomic.AddInt64(&p.stats.SuccessJobs, 1)
				p.resultChan <- job
				continue
			}

			logger.Infof("Uploading: %s", job.FilePath)
			job.SetStage(StageUpload)

			if err := uploader.Upload(ctx, job.FilePath); err != nil {
				job.SetError(err)
				atomic.AddInt64(&p.stats.FailedJobs, 1)
				logger.Errorf("Upload failed for %s: %v", job.FilePath, err)
			} else {
				atomic.AddInt64(&p.stats.UploadJobs, 1)
				atomic.AddInt64(&p.stats.SuccessJobs, 1)
				logger.Infof("Upload completed: %s", job.FilePath)
			}

			p.resultChan <- job
		}
	}
}

func (p *Pipeline) collectResults(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case job := <-p.resultChan:
			if job == nil {
				return
			}
			if job.Error != nil {
				logger.Warnf("Pipeline job failed for %s: %v", job.Database, job.Error)
			} else {
				logger.Infof("Pipeline job completed: %s, %s", job.Database, job.FilePath)
			}
		}
	}
}

func (p *Pipeline) Wait() {
	close(p.compressChan)
	close(p.encryptChan)
	close(p.uploadChan)
	p.wg.Wait()
	close(p.resultChan)
}

func (p *Pipeline) GetStats() PipelineStats {
	return PipelineStats{
		TotalJobs:    atomic.LoadInt64(&p.stats.TotalJobs),
		BackupJobs:   atomic.LoadInt64(&p.stats.BackupJobs),
		CompressJobs: atomic.LoadInt64(&p.stats.CompressJobs),
		EncryptJobs:  atomic.LoadInt64(&p.stats.EncryptJobs),
		UploadJobs:   atomic.LoadInt64(&p.stats.UploadJobs),
		SuccessJobs:  atomic.LoadInt64(&p.stats.SuccessJobs),
		FailedJobs:   atomic.LoadInt64(&p.stats.FailedJobs),
	}
}

type Uploader interface {
	Upload(ctx context.Context, filePath string) error
}

func (p *Pipeline) DecryptFile(encryptedPath string) (string, error) {
	ciphertext, err := os.ReadFile(encryptedPath)
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(p.encryptKey)
	if err != nil {
		return "", err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonceSize := gcm.NonceSize()
	if len(ciphertext) < nonceSize {
		return "", io.ErrUnexpectedEOF
	}

	nonce, ciphertext := ciphertext[:nonceSize], ciphertext[nonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", err
	}

	decryptedPath := encryptedPath[:len(encryptedPath)-4]
	if err := os.WriteFile(decryptedPath, plaintext, 0644); err != nil {
		return "", err
	}

	return decryptedPath, nil
}

func (p *Pipeline) DecompressFile(compressedPath string) (string, error) {
	input, err := os.Open(compressedPath)
	if err != nil {
		return "", err
	}
	defer input.Close()

	gzipReader, err := gzip.NewReader(input)
	if err != nil {
		return "", err
	}
	defer gzipReader.Close()

	decompressedPath := compressedPath[:len(compressedPath)-3]
	output, err := os.Create(decompressedPath)
	if err != nil {
		return "", err
	}
	defer output.Close()

	if _, err := io.Copy(output, gzipReader); err != nil {
		return "", err
	}

	return decompressedPath, nil
}

package storage

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"

	"monitor-agent/internal/collector"
)

type MetricsRecord struct {
	Timestamp     time.Time `json:"timestamp"`
	CPUUsage      float64   `json:"cpu_usage"`
	MemoryUsage   float64   `json:"memory_usage"`
	MemoryTotal   uint64    `json:"memory_total"`
	MemoryUsed    uint64    `json:"memory_used"`
	GPUMetrics    []GPURecord `json:"gpu_metrics,omitempty"`
}

type GPURecord struct {
	Index             int     `json:"index"`
	Name              string  `json:"name"`
	MemoryUsagePercent float64 `json:"memory_usage_percent"`
	Temperature       float64 `json:"temperature"`
	PowerUsage        float64 `json:"power_usage"`
	GPUUtilization    float64 `json:"gpu_utilization"`
}

type Storage struct {
	mu         sync.RWMutex
	baseDir    string
	maxDays    int
	currentFile *os.File
	writer     *bufio.Writer
	currentDate string
}

func NewStorage(baseDir string, maxDays int) (*Storage, error) {
	if baseDir == "" {
		baseDir = "./data"
	}
	if maxDays <= 0 {
		maxDays = 7
	}

	if err := os.MkdirAll(baseDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create storage directory: %w", err)
	}

	s := &Storage{
		baseDir: baseDir,
		maxDays: maxDays,
	}

	if err := s.rotateFile(); err != nil {
		return nil, err
	}

	go s.cleanupLoop()

	return s, nil
}

func (s *Storage) getFileName(date string) string {
	return filepath.Join(s.baseDir, fmt.Sprintf("metrics_%s.jsonl", date))
}

func (s *Storage) rotateFile() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	today := time.Now().Format("2006-01-02")
	if today == s.currentDate && s.currentFile != nil {
		return nil
	}

	if s.currentFile != nil {
		s.writer.Flush()
		s.currentFile.Close()
	}

	filename := s.getFileName(today)
	file, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("failed to open metrics file: %w", err)
	}

	s.currentFile = file
	s.writer = bufio.NewWriter(file)
	s.currentDate = today

	return nil
}

func (s *Storage) Save(metrics *collector.Metrics) error {
	if err := s.rotateFile(); err != nil {
		return err
	}

	record := MetricsRecord{
		Timestamp:   metrics.Timestamp,
		CPUUsage:    metrics.CPUUsage,
		MemoryUsage: metrics.MemoryUsage,
		MemoryTotal: metrics.MemoryTotal,
		MemoryUsed:  metrics.MemoryUsed,
	}

	for _, gpu := range metrics.GPUs {
		record.GPUMetrics = append(record.GPUMetrics, GPURecord{
			Index:              gpu.Index,
			Name:               gpu.Name,
			MemoryUsagePercent: gpu.MemoryUsagePercent,
			Temperature:        gpu.Temperature,
			PowerUsage:         gpu.PowerUsage,
			GPUUtilization:     gpu.GPUUtilization,
		})
	}

	data, err := json.Marshal(record)
	if err != nil {
		return err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, err := s.writer.Write(data); err != nil {
		return err
	}
	if _, err := s.writer.WriteString("\n"); err != nil {
		return err
	}

	return s.writer.Flush()
}

func (s *Storage) Query(startTime, endTime time.Time) ([]MetricsRecord, error) {
	var results []MetricsRecord

	startDate := startTime.Format("2006-01-02")
	endDate := endTime.Format("2006-01-02")

	current := startTime
	for !current.After(endTime) {
		dateStr := current.Format("2006-01-02")
		filename := s.getFileName(dateStr)

		records, err := s.readFile(filename, startTime, endTime)
		if err != nil && !os.IsNotExist(err) {
			return nil, err
		}
		results = append(results, records...)

		current = current.AddDate(0, 0, 1)
		if dateStr == endDate {
			break
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Timestamp.Before(results[j].Timestamp)
	})

	return results, nil
}

func (s *Storage) readFile(filename string, startTime, endTime time.Time) ([]MetricsRecord, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var results []MetricsRecord
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		var record MetricsRecord
		if err := json.Unmarshal([]byte(line), &record); err != nil {
			continue
		}

		if (record.Timestamp.Equal(startTime) || record.Timestamp.After(startTime)) &&
			(record.Timestamp.Equal(endTime) || record.Timestamp.Before(endTime)) {
			results = append(results, record)
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return results, nil
}

func (s *Storage) cleanupLoop() {
	ticker := time.NewTicker(1 * time.Hour)
	defer ticker.Stop()

	for range ticker.C {
		s.cleanupOldFiles()
	}
}

func (s *Storage) cleanupOldFiles() {
	s.mu.RLock()
	baseDir := s.baseDir
	maxDays := s.maxDays
	s.mu.RUnlock()

	files, err := filepath.Glob(filepath.Join(baseDir, "metrics_*.jsonl"))
	if err != nil {
		return
	}

	cutoff := time.Now().AddDate(0, 0, -maxDays)

	for _, file := range files {
		info, err := os.Stat(file)
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			os.Remove(file)
		}
	}
}

func (s *Storage) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.writer != nil {
		s.writer.Flush()
	}
	if s.currentFile != nil {
		return s.currentFile.Close()
	}
	return nil
}

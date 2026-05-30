package thanos

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"time"

	"github.com/golang/snappy"
	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/downsampling"

	"github.com/prometheus/common/model"
	prompb "github.com/prometheus/prometheus/prompb"
)

type Writer struct {
	cfg       config.ThanosConfig
	namespace string
	client    *http.Client
}

type WriteResult struct {
	SuccessCount int
	FailedCount  int
	TotalPoints  int
	Duration     time.Duration
	Error        error
}

func NewWriter(cfg config.ThanosConfig, namespace string) (*Writer, error) {
	transport := &http.Transport{
		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 100,
		IdleConnTimeout:     90 * time.Second,
	}

	if cfg.UseTLS {
		if cfg.TLSCertPath != "" && cfg.TLSKeyPath != "" {
			cert, err := tls.LoadX509KeyPair(cfg.TLSCertPath, cfg.TLSKeyPath)
			if err != nil {
				return nil, fmt.Errorf("failed to load TLS certificates: %w", err)
			}
			transport.TLSClientConfig = &tls.Config{
				Certificates: []tls.Certificate{cert},
			}
		} else {
			transport.TLSClientConfig = &tls.Config{
				InsecureSkipVerify: false,
			}
		}
	}

	client := &http.Client{
		Transport: transport,
		Timeout:   cfg.Timeout,
	}

	return &Writer{
		cfg:       cfg,
		namespace: namespace,
		client:    client,
	}, nil
}

func (w *Writer) Write(ctx context.Context, points []downsampling.DownsampledPoint) (*WriteResult, error) {
	result := &WriteResult{
		TotalPoints: len(points),
	}

	if len(points) == 0 {
		return result, nil
	}

	startTime := time.Now()

	batchSize := w.cfg.BatchSize
	if batchSize <= 0 {
		batchSize = 1000
	}

	for i := 0; i < len(points); i += batchSize {
		end := i + batchSize
		if end > len(points) {
			end = len(points)
		}

		batch := points[i:end]
		batchResult, err := w.writeBatch(ctx, batch)
		if err != nil {
			result.FailedCount += len(batch)
			result.Error = err
			log.Printf("Failed to write batch %d-%d: %v", i, end, err)
			continue
		}

		result.SuccessCount += batchResult.SuccessCount
		result.FailedCount += batchResult.FailedCount
	}

	result.Duration = time.Since(startTime)
	return result, nil
}

func (w *Writer) writeBatch(ctx context.Context, points []downsampling.DownsampledPoint) (*WriteResult, error) {
	result := &WriteResult{
		TotalPoints: len(points),
	}

	tsList := make([]prompb.TimeSeries, 0, len(points))

	for _, point := range points {
		if math.IsNaN(point.Value) || math.IsInf(point.Value, 0) {
			result.FailedCount++
			continue
		}

		labels := w.buildLabels(point)
		samples := []prompb.Sample{
			{
				Value:     point.Value,
				Timestamp: point.Timestamp.UnixNano() / int64(time.Millisecond),
			},
		}

		tsList = append(tsList, prompb.TimeSeries{
			Labels:  labels,
			Samples: samples,
		})
	}

	if len(tsList) == 0 {
		return result, nil
	}

	writeReq := &prompb.WriteRequest{
		Timeseries: tsList,
	}

	data, err := writeReq.Marshal()
	if err != nil {
		result.Error = fmt.Errorf("failed to marshal write request: %w", err)
		result.FailedCount = len(points)
		return result, result.Error
	}

	compressed := snappy.Encode(nil, data)

	err = w.sendWriteRequest(ctx, compressed)
	if err != nil {
		result.Error = err
		result.FailedCount = len(points)
		return result, err
	}

	result.SuccessCount = len(tsList)
	return result, nil
}

func (w *Writer) buildLabels(point downsampling.DownsampledPoint) []prompb.Label {
	labels := make([]prompb.Label, 0, len(point.Labels)+len(w.cfg.ExternalLabels)+2)

	metricName := point.GetMetricName(w.namespace)
	labels = append(labels, prompb.Label{
		Name:  model.MetricNameLabel,
		Value: metricName,
	})

	for k, v := range point.Labels {
		labels = append(labels, prompb.Label{
			Name:  k,
			Value: v,
		})
	}

	for k, v := range w.cfg.ExternalLabels {
		labels = append(labels, prompb.Label{
			Name:  k,
			Value: v,
		})
	}

	return labels
}

func (w *Writer) sendWriteRequest(ctx context.Context, compressedData []byte) error {
	scheme := "http"
	if w.cfg.UseTLS {
		scheme = "https"
	}

	url := fmt.Sprintf("%s://%s/api/v1/receive", scheme, w.cfg.Address)

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(compressedData))
	if err != nil {
		return fmt.Errorf("failed to create HTTP request: %w", err)
	}

	req.Header.Set("Content-Encoding", "snappy")
	req.Header.Set("Content-Type", "application/x-protobuf")
	req.Header.Set("X-Prometheus-Remote-Write-Version", "0.1.0")

	resp, err := w.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send write request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("write request failed with status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

type LabelsResponse struct {
	Status string   `json:"status"`
	Data   []string `json:"data"`
}

func (w *Writer) QueryLabels(ctx context.Context) ([]string, error) {
	scheme := "http"
	if w.cfg.UseTLS {
		scheme = "https"
	}

	url := fmt.Sprintf("%s://%s/api/v1/labels", scheme, w.cfg.Address)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := w.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result LabelsResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	if result.Status != "success" {
		return nil, fmt.Errorf("query failed with status: %s", result.Status)
	}

	return result.Data, nil
}

type TimeSeriesInfo struct {
	Metric     string            `json:"metric"`
	Labels     map[string]string `json:"labels"`
	FirstTime  time.Time         `json:"first_time"`
	LastTime   time.Time         `json:"last_time"`
	SampleCount int64            `json:"sample_count"`
}

func (w *Writer) GetStatus() (map[string]interface{}, error) {
	return map[string]interface{}{
		"enabled":     w.cfg.Enabled,
		"address":     w.cfg.Address,
		"use_tls":     w.cfg.UseTLS,
		"batch_size":  w.cfg.BatchSize,
		"namespace":   w.namespace,
		"external_labels": w.cfg.ExternalLabels,
	}, nil
}

func BuildThanosQuery(metricName string, labels map[string]string) string {
	query := metricName
	if len(labels) == 0 {
		return query
	}

	query += "{"
	first := true
	for k, v := range labels {
		if !first {
			query += ","
		}
		query += fmt.Sprintf(`%s="%s"`, k, v)
		first = false
	}
	query += "}"
	return query
}

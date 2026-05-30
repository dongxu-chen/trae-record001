package prometheus

import (
	"context"
	"fmt"
	"log"
	"math"
	"time"

	"github.com/prometheus/downsampler/pkg/config"

	promapi "github.com/prometheus/client_golang/api"
	promv1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
)

type Client struct {
	api     promv1.API
	cfg     config.PrometheusConfig
	timeout time.Duration
}

type Sample struct {
	Timestamp time.Time
	Value     float64
}

type TimeSeries struct {
	Labels  map[string]string
	Samples []Sample
}

type QueryResult struct {
	Series []TimeSeries
}

func NewClient(cfg config.PrometheusConfig) (*Client, error) {
	client, err := promapi.NewClient(promapi.Config{
		Address: cfg.Address,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create prometheus client: %w", err)
	}

	v1api := promv1.NewAPI(client)

	return &Client{
		api:     v1api,
		cfg:     cfg,
		timeout: cfg.Timeout,
	}, nil
}

func (c *Client) QueryRange(ctx context.Context, query string, start, end time.Time, step time.Duration) (*QueryResult, error) {
	ctx, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()

	rangeQuery := promv1.Range{
		Start: start,
		End:   end,
		Step:  step,
	}

	result, warnings, err := c.api.QueryRange(ctx, query, rangeQuery)
	if err != nil {
		return nil, fmt.Errorf("range query failed: %w", err)
	}

	if len(warnings) > 0 {
		log.Printf("Query warnings: %v", warnings)
	}

	return c.parseResult(result)
}

func (c *Client) Query(ctx context.Context, query string, ts time.Time) (*QueryResult, error) {
	ctx, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()

	result, warnings, err := c.api.Query(ctx, query, ts)
	if err != nil {
		return nil, fmt.Errorf("query failed: %w", err)
	}

	if len(warnings) > 0 {
		log.Printf("Query warnings: %v", warnings)
	}

	return c.parseResult(result)
}

func (c *Client) parseResult(result model.Value) (*QueryResult, error) {
	qr := &QueryResult{}

	switch val := result.(type) {
	case model.Matrix:
		for _, sampleStream := range val {
			ts := TimeSeries{
				Labels:  make(map[string]string),
				Samples: make([]Sample, 0, len(sampleStream.Values)),
			}
			for k, v := range sampleStream.Metric {
				ts.Labels[string(k)] = string(v)
			}
			for _, sample := range sampleStream.Values {
				if math.IsNaN(float64(sample.Value)) {
					continue
				}
				ts.Samples = append(ts.Samples, Sample{
					Timestamp: sample.Timestamp.Time(),
					Value:     float64(sample.Value),
				})
			}
			qr.Series = append(qr.Series, ts)
		}

	case model.Vector:
		for _, sample := range val {
			if math.IsNaN(float64(sample.Value)) {
				continue
			}
			ts := TimeSeries{
				Labels:  make(map[string]string),
				Samples: []Sample{},
			}
			for k, v := range sample.Metric {
				ts.Labels[string(k)] = string(v)
			}
			ts.Samples = append(ts.Samples, Sample{
				Timestamp: sample.Timestamp.Time(),
				Value:     float64(sample.Value),
			})
			qr.Series = append(qr.Series, ts)
		}

	default:
		return nil, fmt.Errorf("unsupported result type: %T", result)
	}

	return qr, nil
}

func (c *Client) GetMetricSeries(ctx context.Context, match string, start, end time.Time) ([]map[string]string, error) {
	ctx, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()

	matcher := []string{match}
	result, warnings, err := c.api.Series(ctx, matcher, start, end)
	if err != nil {
		return nil, fmt.Errorf("series query failed: %w", err)
	}

	if len(warnings) > 0 {
		log.Printf("Series query warnings: %v", warnings)
	}

	labelsList := make([]map[string]string, 0, len(result))
	for _, lbls := range result {
		labels := make(map[string]string)
		for k, v := range lbls {
			labels[string(k)] = string(v)
		}
		labelsList = append(labelsList, labels)
	}

	return labelsList, nil
}

func (c *Client) GetLabelValues(ctx context.Context, labelName string, match string, start, end time.Time) ([]string, error) {
	ctx, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()

	matcher := []string{match}
	result, warnings, err := c.api.LabelValues(ctx, labelName, matcher, start, end)
	if err != nil {
		return nil, fmt.Errorf("label values query failed: %w", err)
	}

	if len(warnings) > 0 {
		log.Printf("Label values query warnings: %v", warnings)
	}

	values := make([]string, 0, len(result))
	for _, v := range result {
		values = append(values, string(v))
	}

	return values, nil
}

func BuildMatchQuery(match string, labels map[string]string) string {
	if len(labels) == 0 {
		return match
	}

	query := match
	base := query[:len(query)-1]
	for k, v := range labels {
		if k == "__name__" {
			continue
		}
		base += fmt.Sprintf(`,%s="%s"`, k, v)
	}
	return base + "}"
}

func (c *Client) QueryRawDataForRule(ctx context.Context, rule config.MetricRule, start, end time.Time) (*QueryResult, error) {
	step, err := determineRawStep(start, end)
	if err != nil {
		return nil, err
	}

	return c.QueryRange(ctx, rule.Match, start, end, step)
}

func determineRawStep(start, end time.Time) (time.Duration, error) {
	duration := end.Sub(start)
	if duration <= 0 {
		return 0, fmt.Errorf("end time must be after start time")
	}

	points := duration / (15 * time.Second)
	if points > 11000 {
		return 15 * time.Second, nil
	}
	if points > 1000 {
		return duration / 1000, nil
	}
	return 15 * time.Second, nil
}

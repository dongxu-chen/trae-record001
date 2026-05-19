package metrics

import (
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/prometheus/prometheus/model/labels"
)

type MetricSpec struct {
	Name   string            `json:"name"`
	Labels map[string]string `json:"labels"`
	Values []TimestampedValue `json:"values"`
}

type TimestampedValue struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
}

type MetricsConfig struct {
	StartTime  time.Time    `json:"start_time"`
	EndTime    time.Time    `json:"end_time"`
	Step       Duration     `json:"step"`
	Metrics    []MetricSpec `json:"metrics"`
}

type Duration struct {
	time.Duration
}

func (d *Duration) UnmarshalJSON(b []byte) error {
	var s string
	if err := json.Unmarshal(b, &s); err != nil {
		return err
	}
	dur, err := time.ParseDuration(s)
	if err != nil {
		return err
	}
	d.Duration = dur
	return nil
}

type Metric struct {
	Labels labels.Labels
	Value  float64
}

type TimeSeriesPoint struct {
	Timestamp int64
	Value     float64
}

type TimeSeries struct {
	Labels labels.Labels
	Points []TimeSeriesPoint
}

type Simulator struct {
	metrics   []MetricSpec
	startTime time.Time
	endTime   time.Time
	step      time.Duration
}

func NewSimulator() *Simulator {
	return &Simulator{
		startTime: time.Now().Add(-10 * time.Minute),
		endTime:   time.Now(),
		step:      15 * time.Second,
	}
}

func (s *Simulator) SetTimeRange(start, end time.Time) {
	s.startTime = start
	s.endTime = end
}

func (s *Simulator) SetStep(step time.Duration) {
	s.step = step
}

func (s *Simulator) StartTime() time.Time {
	return s.startTime
}

func (s *Simulator) EndTime() time.Time {
	return s.endTime
}

func (s *Simulator) Step() time.Duration {
	return s.step
}

func (s *Simulator) LoadFromFile(filename string) error {
	data, err := os.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("failed to read metrics file: %w", err)
	}

	var config MetricsConfig
	if err := json.Unmarshal(data, &config); err != nil {
		return fmt.Errorf("failed to parse metrics json: %w", err)
	}

	if !config.StartTime.IsZero() {
		s.startTime = config.StartTime
	}
	if !config.EndTime.IsZero() {
		s.endTime = config.EndTime
	}
	if config.Step.Duration > 0 {
		s.step = config.Step.Duration
	}

	s.metrics = config.Metrics
	return nil
}

func (s *Simulator) AddMetric(name string, lbls map[string]string, values ...float64) {
	spec := MetricSpec{
		Name:   name,
		Labels: lbls,
	}

	// 如果提供了值，则均匀分布在时间范围内
	if len(values) > 0 {
		t := s.startTime
		stepCount := int(s.endTime.Sub(s.startTime) / s.step)
		valuesPerStep := len(values)
		for i := 0; i < stepCount && i < valuesPerStep; i++ {
			spec.Values = append(spec.Values, TimestampedValue{
				Timestamp: t,
				Value:     values[i%valuesPerStep],
			})
			t = t.Add(s.step)
		}
	}

	s.metrics = append(s.metrics, spec)
}

func (s *Simulator) AddMetricWithConstantValue(name string, lbls map[string]string, value float64) {
	spec := MetricSpec{
		Name:   name,
		Labels: lbls,
	}

	for t := s.startTime; !t.After(s.endTime); t = t.Add(s.step) {
		spec.Values = append(spec.Values, TimestampedValue{
			Timestamp: t,
			Value:     value,
		})
	}

	s.metrics = append(s.metrics, spec)
}

func (s *Simulator) AddMetricWithTransitions(name string, lbls map[string]string, transitions []TimeTransition) {
	spec := MetricSpec{
		Name:   name,
		Labels: lbls,
	}

	currentValue := 0.0
	transitionIdx := 0

	for t := s.startTime; !t.After(s.endTime); t = t.Add(s.step) {
		for transitionIdx < len(transitions) && !t.Before(transitions[transitionIdx].Time) {
			currentValue = transitions[transitionIdx].Value
			transitionIdx++
		}
		spec.Values = append(spec.Values, TimestampedValue{
			Timestamp: t,
			Value:     currentValue,
		})
	}

	s.metrics = append(s.metrics, spec)
}

type TimeTransition struct {
	Time  time.Time
	Value float64
}

func (s *Simulator) GenerateDefaultMetrics() {
	s.AddMetricWithConstantValue("up", map[string]string{"job": "node_exporter", "instance": "localhost:9100"}, 1)
	s.AddMetricWithConstantValue("up", map[string]string{"job": "api_server", "instance": "localhost:8080"}, 0)
	s.AddMetricWithConstantValue("up", map[string]string{"job": "database", "instance": "localhost:5432"}, 1)

	memTotal := 16 * 1024 * 1024 * 1024.0
	s.AddMetricWithConstantValue("node_memory_MemTotal_bytes", map[string]string{"job": "node_exporter", "instance": "localhost:9100"}, memTotal)
	s.AddMetricWithConstantValue("node_memory_MemAvailable_bytes", map[string]string{"job": "node_exporter", "instance": "localhost:9100"}, 2*1024*1024*1024)

	s.AddMetricWithConstantValue("process_open_fds", map[string]string{"job": "api_server", "instance": "localhost:8080"}, 470)
	s.AddMetricWithConstantValue("process_max_fds", map[string]string{"job": "api_server", "instance": "localhost:8080"}, 512)
}

func (s *Simulator) BuildTimeSeries() []TimeSeries {
	var result []TimeSeries

	for _, m := range s.metrics {
		lbls := labels.Labels{
			{Name: "__name__", Value: m.Name},
		}
		for k, v := range m.Labels {
			lbls = append(lbls, labels.Label{Name: k, Value: v})
		}

		var points []TimeSeriesPoint
		for _, val := range m.Values {
			points = append(points, TimeSeriesPoint{
				Timestamp: val.Timestamp.UnixMilli(),
				Value:     val.Value,
			})
		}

		result = append(result, TimeSeries{
			Labels: lbls,
			Points: points,
		})
	}

	return result
}

func (s *Simulator) GetMetricAtTime(lbls labels.Labels, ts int64) (float64, bool) {
	for _, tsData := range s.BuildTimeSeries() {
		if labels.Equal(tsData.Labels, lbls) {
			for _, p := range tsData.Points {
				if p.Timestamp == ts {
					return p.Value, true
				}
			}
			if len(tsData.Points) > 0 {
				return tsData.Points[len(tsData.Points)-1].Value, true
			}
		}
	}
	return 0, false
}

func (s *Simulator) GetMetrics() []MetricSpec {
	return s.metrics
}

func (s *Simulator) EvalTimestamps() []int64 {
	var timestamps []int64
	for t := s.startTime; !t.After(s.endTime); t = t.Add(s.step) {
		timestamps = append(timestamps, t.UnixMilli())
	}
	return timestamps
}

package detector

import (
	"fmt"
	"math"
	"time"

	"anomaly-detector/model"
)

type Detector struct {
	config model.DetectionConfig
}

func NewDetector(config model.DetectionConfig) *Detector {
	return &Detector{config: config}
}

func (d *Detector) GetConfig() model.DetectionConfig {
	return d.config
}

func (d *Detector) Detect(ts model.TimeSeries) []model.Anomaly {
	if len(ts.Points) < 10 {
		return nil
	}

	data := make([]float64, len(ts.Points))
	for i, p := range ts.Points {
		data[i] = p.Value
	}

	period := d.config.Period
	if d.config.EnablePeriodDetect || period <= 0 {
		detectedPeriod := DetectPeriod(data, d.config.MinPeriod, d.config.MaxPeriod)
		if detectedPeriod > 0 {
			period = detectedPeriod
		} else {
			period = d.config.Period
			if period <= 0 {
				period = len(data) / 10
				if period < 2 {
					period = 2
				}
			}
		}
	}

	maxAnomalies := d.config.MaxAnomalies
	if maxAnomalies <= 0 {
		maxAnomalies = 0.1
	}
	maxK := int(float64(len(data)) * maxAnomalies)
	if maxK < 1 {
		maxK = 1
	}
	if maxK > len(data)/2 {
		maxK = len(data) / 2
	}

	alpha := d.config.Alpha
	if alpha <= 0 {
		alpha = 0.05
	}

	direction := string(d.config.Direction)
	if direction == "" {
		direction = "both"
	}

	sesdResults := S_ESDDetect(data, period, maxK, alpha, direction)

	anomalies := make([]model.Anomaly, 0, len(sesdResults))
	for _, r := range sesdResults {
		if !r.IsAnomaly || r.Index >= len(ts.Points) {
			continue
		}

		anomalyDir := model.DirectionBoth
		if r.Value > r.Expected {
			anomalyDir = model.DirectionUp
		} else if r.Value < r.Expected {
			anomalyDir = model.DirectionDown
		}

		if direction == "up" && anomalyDir != model.DirectionUp {
			continue
		}
		if direction == "down" && anomalyDir != model.DirectionDown {
			continue
		}

		anomaly := model.Anomaly{
			ID:        fmt.Sprintf("%s-%d-%d", ts.Name, r.Index, time.Now().UnixNano()),
			Metric:    ts.Name,
			Labels:    ts.Labels,
			Timestamp: ts.Points[r.Index].Timestamp,
			Value:     r.Value,
			Expected:  r.Expected,
			Deviation: r.Deviation,
			Direction: anomalyDir,
			Score:     r.Score,
			ClusterID: -1,
		}

		anomalies = append(anomalies, anomaly)
	}

	return anomalies
}

func (d *Detector) DetectWithDirection(ts model.TimeSeries, direction model.AnomalyDirection) []model.Anomaly {
	originalDirection := d.config.Direction
	d.config.Direction = direction
	result := d.Detect(ts)
	d.config.Direction = originalDirection
	return result
}

func (d *Detector) DetectBatch(series []model.TimeSeries) []model.Anomaly {
	var allAnomalies []model.Anomaly
	for _, ts := range series {
		anomalies := d.Detect(ts)
		allAnomalies = append(allAnomalies, anomalies...)
	}
	return allAnomalies
}

func (d *Detector) GetSeasonalComponents(ts model.TimeSeries) (trend, seasonal, remainder []float64) {
	if len(ts.Points) < 10 {
		return nil, nil, nil
	}

	data := make([]float64, len(ts.Points))
	for i, p := range ts.Points {
		data[i] = p.Value
	}

	period := d.config.Period
	if period <= 0 {
		period = 12
	}

	result := STLDecompose(data, period, 5)
	return result.Trend, result.Seasonal, result.Remainder
}

func (d *Detector) GetAnomalyScores(ts model.TimeSeries) []float64 {
	if len(ts.Points) < 10 {
		return nil
	}

	data := make([]float64, len(ts.Points))
	for i, p := range ts.Points {
		data[i] = p.Value
	}

	period := d.config.Period
	if period <= 0 {
		period = 12
	}

	stlResult := STLDecompose(data, period, 3)

	m := median(stlResult.Remainder)
	madVal := mad(stlResult.Remainder)
	if madVal == 0 {
		madVal = 1
	}

	scores := make([]float64, len(stlResult.Remainder))
	for i, r := range stlResult.Remainder {
		scores[i] = math.Abs(r-m) / (1.4826 * madVal)
	}

	return scores
}

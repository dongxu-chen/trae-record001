package rootcause

import (
	"fmt"
	"math"
	"sort"
	"time"

	"anomaly-detector/alignment"
	"anomaly-detector/model"
)

type RootCauseAnalyzer struct {
	correlationThreshold float64
	leadTimeWindow       time.Duration
}

func NewRootCauseAnalyzer(correlationThreshold float64, leadTimeWindow time.Duration) *RootCauseAnalyzer {
	if correlationThreshold <= 0 {
		correlationThreshold = 0.5
	}
	if leadTimeWindow <= 0 {
		leadTimeWindow = 10 * time.Minute
	}
	return &RootCauseAnalyzer{
		correlationThreshold: correlationThreshold,
		leadTimeWindow:       leadTimeWindow,
	}
}

func (r *RootCauseAnalyzer) Analyze(
	anomaly model.Anomaly,
	allAnomalies []model.Anomaly,
	seriesMap map[string][]float64,
	correlationMatrix map[string]map[string]float64,
) model.RootCauseResult {
	var rootCauses []model.RootCause

	relatedMetrics := r.findRelatedMetrics(anomaly.Metric, correlationMatrix)

	anomalyMap := make(map[string][]model.Anomaly)
	for _, a := range allAnomalies {
		anomalyMap[a.Metric] = append(anomalyMap[a.Metric], a)
	}

	for _, related := range relatedMetrics {
		relatedAnomalies := anomalyMap[related.Metric]
		if len(relatedAnomalies) == 0 {
			continue
		}

		for _, relatedAnomaly := range relatedAnomalies {
			timeDiff := relatedAnomaly.Timestamp.Sub(anomaly.Timestamp)

			leadScore := r.computeLeadScore(timeDiff)

			corrScore := math.Abs(related.Correlation)

			deviationScore := r.computeDeviationScore(relatedAnomaly)

			confidence := leadScore*0.4 + corrScore*0.35 + deviationScore*0.25

			if confidence < 0.2 {
				continue
			}

			reason := r.generateReason(anomaly, relatedAnomaly, timeDiff, related.Correlation, confidence)

			var evidence []model.RootCauseEvidence
			evidence = append(evidence, model.RootCauseEvidence{
				Type:        "correlation",
				Description: fmt.Sprintf("与%s的相关系数: %.3f", anomaly.Metric, related.Correlation),
				Value:       related.Correlation,
			})
			evidence = append(evidence, model.RootCauseEvidence{
				Type:        "temporal_lead",
				Description: fmt.Sprintf("时间领先: %s", timeDiff.Round(time.Second)),
				Value:       timeDiff.Seconds(),
			})
			evidence = append(evidence, model.RootCauseEvidence{
				Type:        "deviation",
				Description: fmt.Sprintf("偏差程度: %.2f (评分: %.2f)", relatedAnomaly.Deviation, relatedAnomaly.Score),
				Value:       relatedAnomaly.Score,
			})

			if len(relatedAnomaly.Labels) > 0 {
				evidence = append(evidence, model.RootCauseEvidence{
					Type:        "context",
					Description: fmt.Sprintf("指标标签: %v", relatedAnomaly.Labels),
					Value:       0,
				})
			}

			rc := model.RootCause{
				Metric:      related.Metric,
				Confidence:  confidence,
				Reason:      reason,
				Evidence:    evidence,
				Correlation: related.Correlation,
				LeadTime:    timeDiff,
				Anomaly:     &relatedAnomaly,
			}

			rootCauses = append(rootCauses, rc)
		}
	}

	if len(seriesMap) > 0 {
		causalRoots := r.inferCausalRoots(anomaly, allAnomalies, seriesMap, correlationMatrix)
		rootCauses = append(rootCauses, causalRoots...)
	}

	rootCauses = r.deduplicateCauses(rootCauses)

	sort.Slice(rootCauses, func(i, j int) bool {
		return rootCauses[i].Confidence > rootCauses[j].Confidence
	})

	var topCause *model.RootCause
	if len(rootCauses) > 0 {
		topCause = &rootCauses[0]
	}

	return model.RootCauseResult{
		Anomaly:      anomaly,
		RootCauses:   rootCauses,
		TopCause:     topCause,
		AnalysisTime: time.Now(),
	}
}

func (r *RootCauseAnalyzer) AnalyzeBatch(
	anomalies []model.Anomaly,
	seriesMap map[string][]float64,
	correlationMatrix map[string]map[string]float64,
) []model.RootCauseResult {
	var results []model.RootCauseResult

	analyzed := make(map[string]bool)
	for _, a := range anomalies {
		key := fmt.Sprintf("%s-%d", a.Metric, a.Timestamp.Unix())
		if analyzed[key] {
			continue
		}
		analyzed[key] = true

		result := r.Analyze(a, anomalies, seriesMap, correlationMatrix)
		if len(result.RootCauses) > 0 {
			results = append(results, result)
		}
	}

	sort.Slice(results, func(i, j int) bool {
		if results[i].TopCause == nil {
			return false
		}
		if results[j].TopCause == nil {
			return true
		}
		return results[i].TopCause.Confidence > results[j].TopCause.Confidence
	})

	return results
}

type relatedMetric struct {
	Metric      string
	Correlation float64
}

func (r *RootCauseAnalyzer) findRelatedMetrics(metric string, correlationMatrix map[string]map[string]float64) []relatedMetric {
	var related []relatedMetric

	if corrMap, ok := correlationMatrix[metric]; ok {
		for other, corr := range corrMap {
			if math.Abs(corr) >= r.correlationThreshold {
				related = append(related, relatedMetric{
					Metric:      other,
					Correlation: corr,
				})
			}
		}
	}

	sort.Slice(related, func(i, j int) bool {
		return math.Abs(related[i].Correlation) > math.Abs(related[j].Correlation)
	})

	return related
}

func (r *RootCauseAnalyzer) computeLeadScore(timeDiff time.Duration) float64 {
	if timeDiff <= 0 {
		return 0.1
	}

	leadSeconds := timeDiff.Seconds()
	windowSeconds := r.leadTimeWindow.Seconds()

	if leadSeconds > windowSeconds {
		return 0.0
	}

	return 1.0 - (leadSeconds / windowSeconds)
}

func (r *RootCauseAnalyzer) computeDeviationScore(anomaly model.Anomaly) float64 {
	if anomaly.Score <= 0 {
		return 0.0
	}
	return math.Min(anomaly.Score/5.0, 1.0)
}

func (r *RootCauseAnalyzer) generateReason(targetAnomaly, causeAnomaly model.Anomaly, timeDiff time.Duration, correlation, confidence float64) string {
	var direction string
	if causeAnomaly.Direction == model.DirectionUp {
		direction = "突增"
	} else if causeAnomaly.Direction == model.DirectionDown {
		direction = "突降"
	} else {
		direction = "异常"
	}

	var targetDirection string
	if targetAnomaly.Direction == model.DirectionUp {
		targetDirection = "上升"
	} else if targetAnomaly.Direction == model.DirectionDown {
		targetDirection = "下降"
	} else {
		targetDirection = "变化"
	}

	var confidenceLevel string
	if confidence >= 0.7 {
		confidenceLevel = "高"
	} else if confidence >= 0.4 {
		confidenceLevel = "中"
	} else {
		confidenceLevel = "低"
	}

	if timeDiff > 0 && timeDiff <= r.leadTimeWindow {
		return fmt.Sprintf("[%s置信度] %s%s(偏差%.1f)领先%.0f秒导致%s%s，相关系数%.2f",
			confidenceLevel, causeAnomaly.Metric, direction, causeAnomaly.Deviation,
			timeDiff.Seconds(), targetAnomaly.Metric, targetDirection, correlation)
	}

	if math.Abs(correlation) >= 0.7 {
		return fmt.Sprintf("[%s置信度] %s%s与%s%s强相关(%.2f)，可能为同一根因",
			confidenceLevel, causeAnomaly.Metric, direction, targetAnomaly.Metric, targetDirection, correlation)
	}

	return fmt.Sprintf("[%s置信度] %s%s可能与%s%s相关(%.2f)",
		confidenceLevel, causeAnomaly.Metric, direction, targetAnomaly.Metric, targetDirection, correlation)
}

func (r *RootCauseAnalyzer) inferCausalRoots(
	anomaly model.Anomaly,
	allAnomalies []model.Anomaly,
	seriesMap map[string][]float64,
	correlationMatrix map[string]map[string]float64,
) []model.RootCause {
	var causes []model.RootCause

	data, ok := seriesMap[anomaly.Metric]
	if !ok || len(data) < 20 {
		return nil
	}

	for metricName, otherData := range seriesMap {
		if metricName == anomaly.Metric {
			continue
		}
		if len(otherData) < 20 {
			continue
		}

		bestLag := 0
		bestCorr := 0.0
		maxLag := minInt(len(data)/4, 20)

		for lag := 1; lag <= maxLag; lag++ {
			if lag >= len(otherData) || lag >= len(data) {
				continue
			}
			minLen := minInt(len(otherData)-lag, len(data))
			if minLen < 10 {
				continue
			}

			a := make([]float64, minLen)
			b := make([]float64, minLen)
			copy(a, otherData[lag:lag+minLen])
			copy(b, data[:minLen])

			corr := alignment.CrossCorrelationWithDTW(a, b)

			if math.Abs(corr) > math.Abs(bestCorr) {
				bestCorr = corr
				bestLag = lag
			}
		}

		if math.Abs(bestCorr) >= r.correlationThreshold && bestLag > 0 {
			existingCorr := 0.0
			if corrMap, ok := correlationMatrix[metricName]; ok {
				if c, ok2 := corrMap[anomaly.Metric]; ok2 {
					existingCorr = c
				}
			}

			if math.Abs(bestCorr) <= math.Abs(existingCorr)*1.1 {
				continue
			}

			confidence := math.Abs(bestCorr) * 0.6
			if bestLag <= 5 {
				confidence += 0.3
			} else if bestLag <= 10 {
				confidence += 0.15
			}

			var relatedAnomaly *model.Anomaly
			for _, a := range allAnomalies {
				if a.Metric == metricName {
					anomCopy := a
					relatedAnomaly = &anomCopy
					break
				}
			}

			if relatedAnomaly == nil {
				relatedAnomaly = &model.Anomaly{
					Metric:    metricName,
					Score:     math.Abs(bestCorr) * 3,
					Direction: model.DirectionBoth,
				}
			}

			leadTime := time.Duration(bestLag) * time.Minute

			causes = append(causes, model.RootCause{
				Metric:      metricName,
				Confidence:  math.Min(confidence, 1.0),
				Reason:      fmt.Sprintf("滞后相关分析: %s领先%d个时间点(相关%.3f)，可能为因果源", metricName, bestLag, bestCorr),
				Evidence: []model.RootCauseEvidence{
					{
						Type:        "lagged_correlation",
						Description: fmt.Sprintf("滞后%d期的相关系数: %.3f", bestLag, bestCorr),
						Value:       bestCorr,
					},
				},
				Correlation: bestCorr,
				LeadTime:    leadTime,
				Anomaly:     relatedAnomaly,
			})
		}
	}

	return causes
}

func (r *RootCauseAnalyzer) deduplicateCauses(causes []model.RootCause) []model.RootCause {
	seen := make(map[string]int)
	var result []model.RootCause

	for _, c := range causes {
		if idx, ok := seen[c.Metric]; ok {
			if c.Confidence > result[idx].Confidence {
				result[idx] = c
			}
		} else {
			seen[c.Metric] = len(result)
			result = append(result, c)
		}
	}

	return result
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

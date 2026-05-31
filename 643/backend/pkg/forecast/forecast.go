package forecast

import (
	"capacity-planner/pkg/models"
	"math"
	"time"

	"github.com/montanaflynn/stats"
)

type ForecastAlgorithm interface {
	Predict(data []float64, steps int) []float64
}

type HoltWinters struct {
	Alpha    float64
	Beta     float64
	Gamma    float64
	Seasonal int
}

func NewHoltWinters(seasonal int) *HoltWinters {
	return &HoltWinters{
		Alpha:    0.3,
		Beta:     0.1,
		Gamma:    0.1,
		Seasonal: seasonal,
	}
}

func (hw *HoltWinters) Predict(data []float64, steps int) []float64 {
	n := len(data)
	if n < 2*hw.Seasonal {
		return simpleMovingAverage(data, steps)
	}

	level, trend, seasonals := hw.initialize(data)
	predictions := make([]float64, steps)

	for i := 0; i < steps; i++ {
		seasonIndex := (n + i) % hw.Seasonal
		predictions[i] = (level + float64(i+1)*trend) * seasonals[seasonIndex]
	}

	return predictions
}

func (hw *HoltWinters) initialize(data []float64) (float64, float64, []float64) {
	n := len(data)
	seasonals := make([]float64, hw.Seasonal)

	seasonMeans := make([]float64, hw.Seasonal)
	for i := 0; i < hw.Seasonal; i++ {
		sum := 0.0
		count := 0
		for j := i; j < n; j += hw.Seasonal {
			sum += data[j]
			count++
		}
		seasonMeans[i] = sum / float64(count)
	}

	overallMean, _ := stats.Mean(seasonMeans)
	for i := 0; i < hw.Seasonal; i++ {
		seasonals[i] = seasonMeans[i] / overallMean
	}

	level := overallMean
	trend := (data[hw.Seasonal] - data[0]) / float64(hw.Seasonal)

	return level, trend, seasonals
}

func simpleMovingAverage(data []float64, steps int) []float64 {
	n := len(data)
	if n == 0 {
		return make([]float64, steps)
	}

	window := 7
	if n < window {
		window = n
	}

	sum := 0.0
	for i := n - window; i < n; i++ {
		sum += data[i]
	}
	avg := sum / float64(window)

	growthRate := 0.0
	if n >= 2 {
		growthRate = (data[n-1] - data[0]) / float64(n)
	}

	predictions := make([]float64, steps)
	for i := 0; i < steps; i++ {
		predictions[i] = avg + growthRate*float64(i+1)
		if predictions[i] < 0 {
			predictions[i] = 0
		}
	}

	return predictions
}

type ARIMASimple struct {
	PDQ [3]int
}

func NewARIMASimple() *ARIMASimple {
	return &ARIMASimple{
		PDQ: [3]int{1, 1, 1},
	}
}

func (a *ARIMASimple) Predict(data []float64, steps int) []float64 {
	n := len(data)
	if n < 3 {
		return simpleMovingAverage(data, steps)
	}

	diffData := make([]float64, n-1)
	for i := 1; i < n; i++ {
		diffData[i-1] = data[i] - data[i-1]
	}

	phi, theta := a.estimateParameters(diffData)

	predictions := make([]float64, steps)
	lastValue := data[n-1]
	lastError := 0.0

	if len(diffData) > 0 {
		predictedDiff := phi*diffData[len(diffData)-1] + theta*lastError
		predictions[0] = lastValue + predictedDiff
		lastError = predictedDiff - diffData[len(diffData)-1]
	} else {
		predictions[0] = lastValue
	}

	for i := 1; i < steps; i++ {
		predictedDiff := phi * (predictions[i-1] - lastValue)
		predictions[i] = predictions[i-1] + predictedDiff
		if predictions[i] < 0 {
			predictions[i] = 0
		}
		lastValue = predictions[i-1]
	}

	return predictions
}

func (a *ARIMASimple) estimateParameters(data []float64) (float64, float64) {
	n := len(data)
	if n < 2 {
		return 0.5, 0.1
	}

	var sumXY, sumX2, sumY float64
	var mean float64

	for _, v := range data {
		mean += v
	}
	mean /= float64(n)

	for i := 1; i < n; i++ {
		x := data[i-1] - mean
		y := data[i] - mean
		sumXY += x * y
		sumX2 += x * x
		sumY += y
	}

	phi := 0.5
	if sumX2 > 0 {
		phi = sumXY / sumX2
	}

	phi = math.Max(-0.9, math.Min(0.9, phi))
	theta := 0.1

	return phi, theta
}

func ForecastTraffic(serviceID string, historicalData []models.TrafficData, forecastDays int) models.TrafficForecast {
	n := len(historicalData)
	dataPoints := make([]float64, n)
	for i, d := range historicalData {
		dataPoints[i] = d.RequestsPerSec
	}

	hw := NewHoltWinters(7)
	predicted := hw.Predict(dataPoints, forecastDays)

	var growthRate float64
	if n > 0 && len(predicted) > 0 {
		recentAvg := 0.0
		recentCount := 0
		for i := max(0, n-7); i < n; i++ {
			recentAvg += dataPoints[i]
			recentCount++
		}
		recentAvg /= float64(recentCount)

		predictedAvg := 0.0
		for _, p := range predicted {
			predictedAvg += p
		}
		predictedAvg /= float64(len(predicted))

		if recentAvg > 0 {
			growthRate = (predictedAvg - recentAvg) / recentAvg
		}
	}

	lastTimestamp := time.Now()
	if n > 0 {
		lastTimestamp = historicalData[n-1].Timestamp
	}

	predictedData := make([]models.TrafficData, len(predicted))
	for i, p := range predicted {
		predictedData[i] = models.TrafficData{
			Timestamp:      lastTimestamp.Add(time.Duration(i+1) * 24 * time.Hour),
			RequestsPerSec: p,
		}
	}

	return models.TrafficForecast{
		ServiceID:      serviceID,
		ForecastPeriod: time.Duration(forecastDays) * 24 * time.Hour,
		GrowthRate:     growthRate,
		HistoricalData: historicalData,
		PredictedData:  predictedData,
	}
}

func CalculatePeakTraffic(forecast models.TrafficForecast, safetyFactor float64) float64 {
	maxTraffic := 0.0
	for _, d := range forecast.PredictedData {
		if d.RequestsPerSec > maxTraffic {
			maxTraffic = d.RequestsPerSec
		}
	}
	return maxTraffic * safetyFactor
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

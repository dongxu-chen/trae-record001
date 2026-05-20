package handlers

import (
	"math"
	"math/rand"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"prometheus-alert-manager/services"
)

type PromQLHandler struct {
	db *gorm.DB
}

func NewPromQLHandler(db *gorm.DB) *PromQLHandler {
	return &PromQLHandler{db: db}
}

type ValidateRequest struct {
	Expr string `json:"expr" binding:"required"`
}

type SimulateRequest struct {
	Expr       string                    `json:"expr" binding:"required"`
	For        string                    `json:"for"`
	Metrics    []services.Metric        `json:"metrics"`
	TimeSeries []services.TimeSeriesMetric `json:"time_series"`
}

type SimulateBatchRequest struct {
	Expr         string                    `json:"expr" binding:"required"`
	For          string                    `json:"for"`
	TestScenarios []TestScenario          `json:"test_scenarios" binding:"required"`
}

type TestScenario struct {
	Name       string                    `json:"name" binding:"required"`
	Metrics    []services.Metric        `json:"metrics"`
	TimeSeries []services.TimeSeriesMetric `json:"time_series"`
	Expected   bool                      `json:"expected"`
}

type BatchSimulateResult struct {
	ScenarioName string                   `json:"scenario_name"`
	Passed       bool                     `json:"passed"`
	Expected     bool                     `json:"expected"`
	Actual       *services.SimulateResult `json:"actual"`
	Message      string                   `json:"message"`
}

func (h *PromQLHandler) Validate(c *gin.Context) {
	var req ValidateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := services.ValidatePromQLDetailed(req.Expr)
	c.JSON(http.StatusOK, result)
}

func (h *PromQLHandler) Simulate(c *gin.Context) {
	var req SimulateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Metrics == nil {
		req.Metrics = []services.Metric{}
	}
	if req.TimeSeries == nil {
		req.TimeSeries = []services.TimeSeriesMetric{}
	}

	if len(req.TimeSeries) == 0 && len(req.Metrics) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "either metrics or time_series must be provided"})
		return
	}

	result, err := services.SimulatePromQLWithDuration(req.Expr, req.For, req.Metrics, req.TimeSeries)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *PromQLHandler) SimulateBatch(c *gin.Context) {
	var req SimulateBatchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	results := make([]BatchSimulateResult, 0, len(req.TestScenarios))
	allPassed := true

	for _, scenario := range req.TestScenarios {
		result, err := services.SimulatePromQLWithDuration(req.Expr, req.For, scenario.Metrics, scenario.TimeSeries)
		if err != nil {
			results = append(results, BatchSimulateResult{
				ScenarioName: scenario.Name,
				Passed:       false,
				Expected:     scenario.Expected,
				Actual:       nil,
				Message:      "Error: " + err.Error(),
			})
			allPassed = false
			continue
		}

		actualFiring := result.Firing && (req.For == "" || result.DurationVerified)
		passed := actualFiring == scenario.Expected
		if !passed {
			allPassed = false
		}

		results = append(results, BatchSimulateResult{
			ScenarioName: scenario.Name,
			Passed:       passed,
			Expected:     scenario.Expected,
			Actual:       result,
			Message: func() string {
				if passed {
					return "Test passed"
				}
				return "Test failed: expected " + boolToString(scenario.Expected) + ", got " + boolToString(actualFiring)
			}(),
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"all_passed": allPassed,
		"results":     results,
		"passed":      countPassed(results),
		"failed":      len(results) - countPassed(results),
	})
}

func (h *PromQLHandler) GenerateTestData(c *gin.Context) {
	var req struct {
		Name       string            `json:"name" binding:"required"`
		Labels   map[string]string `json:"labels"`
		Duration string            `json:"duration" binding:"required"`
		Interval string            `json:"interval" binding:"required"`
		Pattern  string            `json:"pattern" binding:"required"`
		StartValue float64           `json:"start_value"`
		EndValue  float64           `json:"end_value"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	duration, err := time.ParseDuration(req.Duration)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid duration: " + err.Error()})
		return
	}

	interval, err := time.ParseDuration(req.Interval)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid interval: " + err.Error()})
		return
	}

	count := int(duration / interval)
	start := time.Now().Add(-duration)

	var valueFunc func(int) float64
	switch req.Pattern {
	case "increasing":
		delta := req.EndValue - req.StartValue
		valueFunc = func(i int) float64 {
			return req.StartValue + delta*float64(i)/float64(count)
		}
	case "decreasing":
		delta := req.StartValue - req.EndValue
		valueFunc = func(i int) float64 {
			return req.StartValue - delta*float64(i)/float64(count)
		}
	case "wave":
		amplitude := (req.EndValue - req.StartValue) / 2
		mid := (req.StartValue + req.EndValue) / 2
		valueFunc = func(i int) float64 {
			return mid + amplitude*math.Sin(2*math.Pi*float64(i)/float64(count))
		}
	case "spike":
		valueFunc = func(i int) float64 {
			if i > count/2 && i < count*3/4 {
				return req.EndValue
			}
			return req.StartValue
		}
	case "random":
		rand.Seed(time.Now().UnixNano())
		delta := req.EndValue - req.StartValue
		valueFunc = func(i int) float64 {
			return req.StartValue + rand.Float64()*delta
		}
	case "constant":
		valueFunc = func(i int) float64 {
			return req.StartValue
		}
	default:
		valueFunc = func(i int) float64 {
			return req.StartValue + float64(i)
		}
	}

	ts := services.GenerateTimeSeries(req.Name, req.Labels, start, interval, count, valueFunc)

	c.JSON(http.StatusOK, gin.H{
		"time_series": ts,
		"point_count": count,
		"duration":    duration.String(),
		"interval":   interval.String(),
	})
}

func boolToString(b bool) string {
	if b {
		return "firing"
	}
	return "not firing"
}

func countPassed(results []BatchSimulateResult) int {
	count := 0
	for _, r := range results {
		if r.Passed {
			count++
		}
	}
	return count
}

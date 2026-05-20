package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
)

type PrometheusHandler struct {
	baseURL string
}

func NewPrometheusHandler() *PrometheusHandler {
	url := os.Getenv("PROMETHEUS_URL")
	if url == "" {
		url = "http://localhost:9090"
	}
	return &PrometheusHandler{baseURL: url}
}

type QueryRequest struct {
	Query string `json:"query" binding:"required"`
	Time  string `json:"time"`
}

func (h *PrometheusHandler) GetRules(c *gin.Context) {
	url := fmt.Sprintf("%s/api/v1/rules", h.baseURL)
	resp, err := http.Get(url)
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": fmt.Sprintf("Failed to connect to Prometheus: %v", err)})
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var result map[string]interface{}
	json.Unmarshal(body, &result)

	c.JSON(resp.StatusCode, result)
}

func (h *PrometheusHandler) GetAlerts(c *gin.Context) {
	url := fmt.Sprintf("%s/api/v1/alerts", h.baseURL)
	resp, err := http.Get(url)
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": fmt.Sprintf("Failed to connect to Prometheus: %v", err)})
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var result map[string]interface{}
	json.Unmarshal(body, &result)

	c.JSON(resp.StatusCode, result)
}

func (h *PrometheusHandler) Query(c *gin.Context) {
	var req QueryRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	url := fmt.Sprintf("%s/api/v1/query", h.baseURL)
	body, _ := json.Marshal(map[string]string{
		"query": req.Query,
		"time":  req.Time,
	})

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": fmt.Sprintf("Failed to connect to Prometheus: %v", err)})
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	var result map[string]interface{}
	json.Unmarshal(respBody, &result)

	c.JSON(resp.StatusCode, result)
}

package model

import "time"

type TimeSeriesPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
}

type TimeSeries struct {
	Name   string            `json:"name"`
	Labels map[string]string `json:"labels"`
	Points []TimeSeriesPoint `json:"points"`
}

type AnomalyDirection string

const (
	DirectionUp   AnomalyDirection = "up"
	DirectionDown AnomalyDirection = "down"
	DirectionBoth AnomalyDirection = "both"
)

type Anomaly struct {
	ID        string           `json:"id"`
	Metric    string           `json:"metric"`
	Labels    map[string]string `json:"labels"`
	Timestamp time.Time        `json:"timestamp"`
	Value     float64          `json:"value"`
	Expected  float64          `json:"expected"`
	Deviation float64          `json:"deviation"`
	Direction AnomalyDirection `json:"direction"`
	Score     float64          `json:"score"`
	ClusterID int              `json:"cluster_id"`
}

type AlertSeverity string

const (
	SeverityCritical AlertSeverity = "critical"
	SeverityWarning  AlertSeverity = "warning"
	SeverityInfo     AlertSeverity = "info"
)

type Alert struct {
	ID          string           `json:"id"`
	Anomalies   []Anomaly       `json:"anomalies"`
	Severity    AlertSeverity   `json:"severity"`
	Title       string           `json:"title"`
	Description string           `json:"description"`
	CreatedAt   time.Time        `json:"created_at"`
	UpdatedAt   time.Time        `json:"updated_at"`
	GroupKey    string           `json:"group_key"`
	Suppressed  bool             `json:"suppressed"`
	Acknowledged bool            `json:"acknowledged"`
}

type CorrelationResult struct {
	MetricA    string  `json:"metric_a"`
	MetricB    string  `json:"metric_b"`
	Coefficient float64 `json:"coefficient"`
	PValue     float64 `json:"_p_value"`
	Significant bool    `json:"significant"`
}

type ClusterResult struct {
	ClusterID  int       `json:"cluster_id"`
	Anomalies  []Anomaly `json:"anomalies"`
	CenterTime time.Time `json:"center_time"`
	Size       int       `json:"size"`
	Severity   AlertSeverity `json:"severity"`
}

type DetectionConfig struct {
	PrometheusURL    string          `json:"prometheus_url"`
	QueryInterval    time.Duration   `json:"query_interval"`
	Lookback         time.Duration   `json:"lookback"`
	MaxAnomalies     float64         `json:"max_anomalies"`
	Alpha            float64         `json:"alpha"`
	Direction        AnomalyDirection `json:"direction"`
	Period           int             `json:"period"`
	EnablePeriodDetect bool          `json:"enable_period_detect"`
	MinPeriod        int             `json:"min_period"`
	MaxPeriod        int             `json:"max_period"`
}

type RootCause struct {
	Metric       string            `json:"metric"`
	Confidence   float64           `json:"confidence"`
	Reason       string            `json:"reason"`
	Evidence     []RootCauseEvidence `json:"evidence"`
	Correlation  float64           `json:"correlation"`
	LeadTime     time.Duration     `json:"lead_time"`
	Anomaly      *Anomaly          `json:"anomaly,omitempty"`
}

type RootCauseEvidence struct {
	Type        string  `json:"type"`
	Description string  `json:"description"`
	Value       float64 `json:"value"`
}

type RootCauseResult struct {
	Anomaly      Anomaly     `json:"anomaly"`
	RootCauses   []RootCause `json:"root_causes"`
	TopCause     *RootCause  `json:"top_cause,omitempty"`
	AnalysisTime time.Time   `json:"analysis_time"`
}

type Prediction struct {
	Metric        string    `json:"metric"`
	PredictedTime time.Time `json:"predicted_time"`
	Direction     AnomalyDirection `json:"direction"`
	Confidence    float64   `json:"confidence"`
	CurrentValue  float64   `json:"current_value"`
	Threshold     float64   `json:"threshold"`
	TrendSlope    float64   `json:"trend_slope"`
	Reason        string    `json:"reason"`
}

type PredictionResult struct {
	Predictions  []Prediction `json:"predictions"`
	AnalysisTime time.Time    `json:"analysis_time"`
	Horizon      time.Duration `json:"horizon"`
}

type InjectionType string

const (
	InjectionSpike      InjectionType = "spike"
	InjectionDrop       InjectionType = "drop"
	InjectionGradual    InjectionType = "gradual"
	InjectionOscillation InjectionType = "oscillation"
)

type InjectionConfig struct {
	Metric      string        `json:"metric"`
	Type        InjectionType `json:"type"`
	Magnitude   float64       `json:"magnitude"`
	StartIndex  int           `json:"start_index"`
	Duration    int           `json:"duration"`
}

type InjectionResult struct {
	InjectedMetric string           `json:"injected_metric"`
	InjectionType  InjectionType    `json:"injection_type"`
	OriginalSeries []float64        `json:"original_series"`
	InjectedSeries []float64        `json:"injected_series"`
	DetectedCount  int              `json:"detected_count"`
	InjectedCount  int              `json:"injected_count"`
	Sensitivity    float64          `json:"sensitivity"`
	DetectionDelay int              `json:"detection_delay"`
	FalsePositiveRate float64       `json:"false_positive_rate"`
	DetectionDetails []DetectionDetail `json:"detection_details"`
}

type DetectionDetail struct {
	Index     int     `json:"index"`
	Detected  bool    `json:"detected"`
	Expected  float64 `json:"expected"`
	Actual    float64 `json:"actual"`
	Score     float64 `json:"score"`
}

type AlertConfig struct {
	GroupWait       time.Duration `json:"group_wait"`
	GroupInterval   time.Duration `json:"group_interval"`
	RepeatInterval  time.Duration `json:"repeat_interval"`
	SuppressionWindow time.Duration `json:"suppression_window"`
	MaxAlertsPerGroup int          `json:"max_alerts_per_group"`
}

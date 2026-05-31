package models

import "time"

type RoutingRule struct {
	ID          string    `json:"id" yaml:"id"`
	Name        string    `json:"name" yaml:"name"`
	Namespace   string    `json:"namespace" yaml:"namespace"`
	Type        string    `json:"type" yaml:"type"`
	ServiceName string    `json:"serviceName" yaml:"serviceName"`
	Status      string    `json:"status" yaml:"status"`
	CreatedAt   time.Time `json:"createdAt" yaml:"createdAt"`
	UpdatedAt   time.Time `json:"updatedAt" yaml:"updatedAt"`
}

type WeightRouting struct {
	RoutingRule `yaml:",inline"`
	Subsets     []SubsetWeight `json:"subsets" yaml:"subsets"`
}

type SubsetWeight struct {
	SubsetName string  `json:"subsetName" yaml:"subsetName"`
	Weight     int     `json:"weight" yaml:"weight"`
	Version    string  `json:"version" yaml:"version"`
}

type HeaderRouting struct {
	RoutingRule `yaml:",inline"`
	MatchRules  []HeaderMatch `json:"matchRules" yaml:"matchRules"`
	TargetSubset string       `json:"targetSubset" yaml:"targetSubset"`
}

type HeaderMatch struct {
	HeaderName string   `json:"headerName" yaml:"headerName"`
	MatchType  string   `json:"matchType" yaml:"matchType"`
	Value      string   `json:"value" yaml:"value"`
	Values     []string `json:"values,omitempty" yaml:"values,omitempty"`
}

type TrafficMirror struct {
	RoutingRule    `yaml:",inline"`
	MirrorService  string `json:"mirrorService" yaml:"mirrorService"`
	MirrorSubset   string `json:"mirrorSubset,omitempty" yaml:"mirrorSubset,omitempty"`
	MirrorPort     int32  `json:"mirrorPort,omitempty" yaml:"mirrorPort,omitempty"`
	SourceService  string `json:"sourceService" yaml:"sourceService"`
	Percentage     int    `json:"percentage" yaml:"percentage"`
}

type FaultInjection struct {
	RoutingRule `yaml:",inline"`
	FaultType   string     `json:"faultType" yaml:"faultType"`
	Percentage  int        `json:"percentage" yaml:"percentage"`
	Delay       *DelaySpec `json:"delay,omitempty" yaml:"delay,omitempty"`
	Abort       *AbortSpec `json:"abort,omitempty" yaml:"abort,omitempty"`
}

type DelaySpec struct {
	FixedDelay string `json:"fixedDelay" yaml:"fixedDelay"`
}

type AbortSpec struct {
	HTTPStatus int32 `json:"httpStatus" yaml:"httpStatus"`
}

type VirtualService struct {
	APIVersion string   `json:"apiVersion" yaml:"apiVersion"`
	Kind       string   `json:"kind" yaml:"kind"`
	Metadata   Metadata `json:"metadata" yaml:"metadata"`
	Spec       VSSpec   `json:"spec" yaml:"spec"`
}

type Metadata struct {
	Name      string            `json:"name" yaml:"name"`
	Namespace string            `json:"namespace" yaml:"namespace"`
	Labels    map[string]string `json:"labels,omitempty" yaml:"labels,omitempty"`
}

type VSSpec struct {
	Hosts    []string   `json:"hosts" yaml:"hosts"`
	Gateways []string   `json:"gateways,omitempty" yaml:"gateways,omitempty"`
	HTTP     []HTTPRoute `json:"http" yaml:"http"`
}

type HTTPRoute struct {
	Match            []HTTPMatch      `json:"match,omitempty" yaml:"match,omitempty"`
	Route            []Destination    `json:"route,omitempty" yaml:"route,omitempty"`
	Mirror           *Destination     `json:"mirror,omitempty" yaml:"mirror,omitempty"`
	MirrorPercentage *Percent         `json:"mirrorPercentage,omitempty" yaml:"mirrorPercentage,omitempty"`
	Fault            *HTTPFaultInjection `json:"fault,omitempty" yaml:"fault,omitempty"`
}

type HTTPMatch struct {
	Headers map[string]StringMatch `json:"headers,omitempty" yaml:"headers,omitempty"`
	URI     *URIMatch              `json:"uri,omitempty" yaml:"uri,omitempty"`
}

type StringMatch struct {
	Exact  string `json:"exact,omitempty" yaml:"exact,omitempty"`
	Prefix string `json:"prefix,omitempty" yaml:"prefix,omitempty"`
	Regex  string `json:"regex,omitempty" yaml:"regex,omitempty"`
}

type URIMatch struct {
	Exact  string `json:"exact,omitempty" yaml:"exact,omitempty"`
	Prefix string `json:"prefix,omitempty" yaml:"prefix,omitempty"`
	Regex  string `json:"regex,omitempty" yaml:"regex,omitempty"`
}

type Destination struct {
	Host   string `json:"host" yaml:"host"`
	Subset string `json:"subset,omitempty" yaml:"subset,omitempty"`
	Port   *Port  `json:"port,omitempty" yaml:"port,omitempty"`
}

type Port struct {
	Number int32 `json:"number" yaml:"number"`
}

type Percent struct {
	Value float64 `json:"value" yaml:"value"`
}

type HTTPFaultInjection struct {
	Delay *DelayFault `json:"delay,omitempty" yaml:"delay,omitempty"`
	Abort *AbortFault `json:"abort,omitempty" yaml:"abort,omitempty"`
}

type DelayFault struct {
	FixedDelay    string  `json:"fixedDelay" yaml:"fixedDelay"`
	Percentage    float64 `json:"percentage,omitempty" yaml:"percentage,omitempty"`
}

type AbortFault struct {
	HTTPStatus    int32   `json:"httpStatus" yaml:"httpStatus"`
	Percentage    float64 `json:"percentage,omitempty" yaml:"percentage,omitempty"`
}

type DestinationRule struct {
	APIVersion string    `json:"apiVersion" yaml:"apiVersion"`
	Kind       string    `json:"kind" yaml:"kind"`
	Metadata   Metadata  `json:"metadata" yaml:"metadata"`
	Spec       DRSpec    `json:"spec" yaml:"spec"`
}

type DRSpec struct {
	Host    string    `json:"host" yaml:"host"`
	Subsets []Subset  `json:"subsets,omitempty" yaml:"subsets,omitempty"`
}

type Subset struct {
	Name   string            `json:"name" yaml:"name"`
	Labels map[string]string `json:"labels" yaml:"labels"`
}

type BlueGreenDeployment struct {
	ID                   string        `json:"id" yaml:"id"`
	Name                 string        `json:"name" yaml:"name"`
	Namespace            string        `json:"namespace" yaml:"namespace"`
	ServiceName          string        `json:"serviceName" yaml:"serviceName"`
	BlueSubset           string        `json:"blueSubset" yaml:"blueSubset"`
	GreenSubset          string        `json:"greenSubset" yaml:"greenSubset"`
	BlueVersion          string        `json:"blueVersion" yaml:"blueVersion"`
	GreenVersion         string        `json:"greenVersion" yaml:"greenVersion"`
	CurrentWeightBlue    int           `json:"currentWeightBlue" yaml:"currentWeightBlue"`
	TargetWeightBlue     int           `json:"targetWeightBlue" yaml:"targetWeightBlue"`
	StepSize             int           `json:"stepSize" yaml:"stepSize"`
	StepIntervalSeconds  int           `json:"stepIntervalSeconds" yaml:"stepIntervalSeconds"`
	AutoRollbackEnabled  bool          `json:"autoRollbackEnabled" yaml:"autoRollbackEnabled"`
	RollbackThreshold    float64       `json:"rollbackThreshold" yaml:"rollbackThreshold"`
	Status               string        `json:"status" yaml:"status"`
	Phase                string        `json:"phase" yaml:"phase"`
	CreatedAt            time.Time     `json:"createdAt" yaml:"createdAt"`
	UpdatedAt            time.Time     `json:"updatedAt" yaml:"updatedAt"`
	DeploymentHistory    []DeploymentStep `json:"deploymentHistory,omitempty" yaml:"deploymentHistory,omitempty"`
}

type DeploymentStep struct {
	Timestamp     time.Time `json:"timestamp" yaml:"timestamp"`
	WeightBlue    int       `json:"weightBlue" yaml:"weightBlue"`
	WeightGreen   int       `json:"weightGreen" yaml:"weightGreen"`
	Success       bool      `json:"success" yaml:"success"`
	ErrorRate     float64   `json:"errorRate" yaml:"errorRate"`
	LatencyP95    float64   `json:"latencyP95" yaml:"latencyP95"`
	Rollback      bool      `json:"rollback" yaml:"rollback"`
	Message       string    `json:"message,omitempty" yaml:"message,omitempty"`
}

type AccessControlRule struct {
	ID            string            `json:"id" yaml:"id"`
	Name          string            `json:"name" yaml:"name"`
	Namespace     string            `json:"namespace" yaml:"namespace"`
	ServiceName   string            `json:"serviceName" yaml:"serviceName"`
	RuleType      string            `json:"ruleType" yaml:"ruleType"`
	ControlType   string            `json:"controlType" yaml:"controlType"`
	ListType      string            `json:"listType" yaml:"listType"`
	IPList        []string          `json:"ipList,omitempty" yaml:"ipList,omitempty"`
	UserIDList    []string          `json:"userIdList,omitempty" yaml:"userIdList,omitempty"`
	HeaderName    string            `json:"headerName,omitempty" yaml:"headerName,omitempty"`
	HeaderValues  []string          `json:"headerValues,omitempty" yaml:"headerValues,omitempty"`
	Priority      int               `json:"priority" yaml:"priority"`
	Status        string            `json:"status" yaml:"status"`
	Description   string            `json:"description,omitempty" yaml:"description,omitempty"`
	CreatedAt     time.Time         `json:"createdAt" yaml:"createdAt"`
	UpdatedAt     time.Time         `json:"updatedAt" yaml:"updatedAt"`
}

type CostEstimateRequest struct {
	ServiceName  string    `json:"serviceName"`
	Namespace    string    `json:"namespace"`
	StartDate    time.Time `json:"startDate"`
	EndDate      time.Time `json:"endDate"`
	TrafficGB    float64   `json:"trafficGB"`
	CrossAZRatio float64   `json:"crossAZRatio"`
	Region       string    `json:"region"`
	CloudProvider string   `json:"cloudProvider"`
}

type CostEstimateResult struct {
	ID                  string  `json:"id"`
	TotalCost           float64 `json:"totalCost"`
	IntraAZCost         float64 `json:"intraAZCost"`
	CrossAZCost         float64 `json:"crossAZCost"`
	IntraAZTrafficGB    float64 `json:"intraAZTrafficGB"`
	CrossAZTrafficGB    float64 `json:"crossAZTrafficGB"`
	CostPerGBIntraAZ    float64 `json:"costPerGBIntraAZ"`
	CostPerGBCrossAZ    float64 `json:"costPerGBCrossAZ"`
	EstimatedRequests   int64   `json:"estimatedRequests"`
	AvgRequestSizeKB    float64 `json:"avgRequestSizeKB"`
	Currency            string  `json:"currency"`
	Region              string  `json:"region"`
	CloudProvider       string  `json:"cloudProvider"`
	GeneratedAt         time.Time `json:"generatedAt"`
	Breakdown           []CostBreakdownItem `json:"breakdown,omitempty"`
}

type CostBreakdownItem struct {
	Name        string  `json:"name"`
	Description string  `json:"description"`
	Amount      float64 `json:"amount"`
	Percentage  float64 `json:"percentage"`
}

type CostConfig struct {
	CloudProvider string                `json:"cloudProvider"`
	Region        string                `json:"region"`
	Currency      string                `json:"currency"`
	IntraAZRate   map[string]float64    `json:"intraAZRate"`
	CrossAZRate   map[string]float64    `json:"crossAZRate"`
}


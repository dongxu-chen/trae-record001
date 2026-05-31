package cost

import (
	"cloud-tag-compliance/internal/cloud"
	"math"
	"sort"
	"strings"
	"time"
)

type ResourceCost struct {
	ResourceID    string            `json:"resourceId"`
	ResourceName  string            `json:"resourceName"`
	ResourceType  cloud.ResourceType `json:"resourceType"`
	Tags          map[string]string `json:"tags"`
	DailyCost     float64           `json:"dailyCost"`
	MonthlyCost   float64           `json:"monthlyCost"`
	Currency      string            `json:"currency"`
	LastUpdated   string            `json:"lastUpdated"`
}

type TagCostSummary struct {
	TagKey        string            `json:"tagKey"`
	TagValue      string            `json:"tagValue"`
	ResourceCount int               `json:"resourceCount"`
	TotalDailyCost    float64       `json:"totalDailyCost"`
	TotalMonthlyCost  float64       `json:"totalMonthlyCost"`
	Percentage    float64           `json:"percentage"`
	Resources     []ResourceCost    `json:"resources,omitempty"`
}

type CostAllocationReport struct {
	ReportDate    string            `json:"reportDate"`
	TotalDailyCost    float64       `json:"totalDailyCost"`
	TotalMonthlyCost  float64       `json:"totalMonthlyCost"`
	Currency      string            `json:"currency"`
	ByTag         map[string][]TagCostSummary `json:"byTag"`
	ByEnvironment []TagCostSummary  `json:"byEnvironment"`
	ByDepartment  []TagCostSummary  `json:"byDepartment"`
	ByCostCenter  []TagCostSummary  `json:"byCostCenter"`
	ByProject     []TagCostSummary  `json:"byProject"`
	Untagged      *TagCostSummary   `json:"untagged,omitempty"`
}

type AllocationEngine struct {
	resourceCosts map[string]ResourceCost
	priceList     map[cloud.ResourceType]float64
}

func NewAllocationEngine() *AllocationEngine {
	engine := &AllocationEngine{
		resourceCosts: make(map[string]ResourceCost),
		priceList: map[cloud.ResourceType]float64{
			cloud.ECS:  15.0,
			cloud.RDS:  25.0,
			cloud.OSS:  0.5,
		},
	}
	return engine
}

func (e *AllocationEngine) CalculateCosts(resources []cloud.Resource) []ResourceCost {
	costs := make([]ResourceCost, 0, len(resources))

	for _, r := range resources {
		dailyCost := e.calculateDailyCost(r)
		monthlyCost := dailyCost * 30

		cost := ResourceCost{
			ResourceID:   r.ID,
			ResourceName: r.Name,
			ResourceType: r.Type,
			Tags:         r.Tags,
			DailyCost:    math.Round(dailyCost*100) / 100,
			MonthlyCost:  math.Round(monthlyCost*100) / 100,
			Currency:     "CNY",
			LastUpdated:  time.Now().Format(time.RFC3339),
		}

		e.resourceCosts[r.ID] = cost
		costs = append(costs, cost)
	}

	return costs
}

func (e *AllocationEngine) calculateDailyCost(resource cloud.Resource) float64 {
	basePrice, ok := e.priceList[resource.Type]
	if !ok {
		basePrice = 10.0
	}

	multiplier := 1.0
	if strings.Contains(strings.ToLower(resource.Name), "large") {
		multiplier *= 2.0
	} else if strings.Contains(strings.ToLower(resource.Name), "xlarge") {
		multiplier *= 4.0
	} else if strings.Contains(strings.ToLower(resource.Name), "small") {
		multiplier *= 0.5
	}

	if strings.Contains(strings.ToLower(resource.Name), "prod") {
		multiplier *= 1.5
	}

	return basePrice * multiplier
}

func (e *AllocationEngine) GenerateReport(resources []cloud.Resource) *CostAllocationReport {
	costs := e.CalculateCosts(resources)

	var totalDaily, totalMonthly float64
	for _, c := range costs {
		totalDaily += c.DailyCost
		totalMonthly += c.MonthlyCost
	}

	report := &CostAllocationReport{
		ReportDate:     time.Now().Format("2006-01-02"),
		TotalDailyCost:  math.Round(totalDaily*100) / 100,
		TotalMonthlyCost: math.Round(totalMonthly*100) / 100,
		Currency:       "CNY",
		ByTag:          make(map[string][]TagCostSummary),
	}

	report.ByEnvironment = e.aggregateByTag(costs, "Environment", totalMonthly)
	report.ByDepartment = e.aggregateByTag(costs, "Department", totalMonthly)
	report.ByCostCenter = e.aggregateByTag(costs, "CostCenter", totalMonthly)
	report.ByProject = e.aggregateByTag(costs, "Project", totalMonthly)

	report.ByTag["Environment"] = report.ByEnvironment
	report.ByTag["Department"] = report.ByDepartment
	report.ByTag["CostCenter"] = report.ByCostCenter
	report.ByTag["Project"] = report.ByProject

	report.Untagged = e.calculateUntagged(costs, totalMonthly)

	return report
}

func (e *AllocationEngine) aggregateByTag(costs []ResourceCost, tagKey string, totalMonthly float64) []TagCostSummary {
	valueMap := make(map[string]*TagCostSummary)

	for _, c := range costs {
		value, exists := c.Tags[tagKey]
		if !exists || value == "" {
			continue
		}

		if _, ok := valueMap[value]; !ok {
			valueMap[value] = &TagCostSummary{
				TagKey:   tagKey,
				TagValue: value,
				Currency: "CNY",
			}
		}

		valueMap[value].ResourceCount++
		valueMap[value].TotalDailyCost += c.DailyCost
		valueMap[value].TotalMonthlyCost += c.MonthlyCost
		valueMap[value].Resources = append(valueMap[value].Resources, c)
	}

	summaries := make([]TagCostSummary, 0, len(valueMap))
	for _, s := range valueMap {
		s.TotalDailyCost = math.Round(s.TotalDailyCost*100) / 100
		s.TotalMonthlyCost = math.Round(s.TotalMonthlyCost*100) / 100
		if totalMonthly > 0 {
			s.Percentage = math.Round((s.TotalMonthlyCost/totalMonthly)*10000) / 100
		}
		summaries = append(summaries, *s)
	}

	sort.Slice(summaries, func(i, j int) bool {
		return summaries[i].TotalMonthlyCost > summaries[j].TotalMonthlyCost
	})

	return summaries
}

func (e *AllocationEngine) calculateUntagged(costs []ResourceCost, totalMonthly float64) *TagCostSummary {
	var untaggedCost float64
	var untaggedCount int

	for _, c := range costs {
		hasTags := false
		for k, v := range c.Tags {
			if k != "" && v != "" {
				hasTags = true
				break
			}
		}
		if !hasTags || len(c.Tags) == 0 {
			untaggedCost += c.MonthlyCost
			untaggedCount++
		}
	}

	if untaggedCount == 0 {
		return nil
	}

	percentage := 0.0
	if totalMonthly > 0 {
		percentage = math.Round((untaggedCost/totalMonthly)*10000) / 100
	}

	return &TagCostSummary{
		TagKey:         "Untagged",
		TagValue:       "Resources without required tags",
		ResourceCount:  untaggedCount,
		TotalDailyCost: math.Round((untaggedCost/30)*100) / 100,
		TotalMonthlyCost: math.Round(untaggedCost*100) / 100,
		Percentage:     percentage,
		Currency:       "CNY",
	}
}

func (e *AllocationEngine) GetCostTrend(resources []cloud.Resource, days int) map[string][]float64 {
	trend := make(map[string][]float64)

	for _, r := range resources {
		dailyCost := e.calculateDailyCost(r)
		costs := make([]float64, days)
		for i := 0; i < days; i++ {
			variation := 0.95 + (float64(i%7)/100)*2
			costs[i] = math.Round(dailyCost*variation*100) / 100
		}
		trend[r.ID] = costs
	}

	return trend
}

func (e *AllocationEngine) GetCostForecast(resources []cloud.Resource, months int) []float64 {
	forecast := make([]float64, months)

	var monthlyTotal float64
	for _, r := range resources {
		monthlyTotal += e.calculateDailyCost(r) * 30
	}

	for i := 0; i < months; i++ {
		growth := 1.0 + (float64(i) * 0.02)
		forecast[i] = math.Round(monthlyTotal*growth*100) / 100
	}

	return forecast
}

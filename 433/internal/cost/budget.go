package cost

import (
	"sort"
	"time"

	"k8s-cost-allocation/internal/config"
)

type BudgetAlert struct {
	Namespace      string  `json:"namespace"`
	CurrentCost    float64 `json:"currentCost"`
	Budget         float64 `json:"budget"`
	Percentage     float64 `json:"percentage"`
	Level          string  `json:"level"`
	Message        string  `json:"message"`
	DaysRemaining  int     `json:"daysRemaining"`
	ProjectedCost  float64 `json:"projectedCost"`
}

type PriceComparison struct {
	Scenario         string  `json:"scenario"`
	MonthlyCPUCost   float64 `json:"monthlyCpuCost"`
	MonthlyMemoryCost float64 `json:"monthlyMemoryCost"`
	TotalMonthlyCost float64 `json:"totalMonthlyCost"`
	UpfrontCost      float64 `json:"upfrontCost,omitempty"`
	AnnualSavings    float64 `json:"annualSavings,omitempty"`
	SavingsPercent   float64 `json:"savingsPercent,omitempty"`
	BreakEvenMonths  float64 `json:"breakEvenMonths,omitempty"`
}

type SpotRecommendation struct {
	Namespace        string  `json:"namespace"`
	CPUCores         float64 `json:"cpuCores"`
	MemoryGB         float64 `json:"memoryGB"`
	OnDemandMonthly  float64 `json:"onDemandMonthly"`
	SpotMonthly      float64 `json:"spotMonthly"`
	MonthlySavings   float64 `json:"monthlySavings"`
	SavingsPercent   float64 `json:"savingsPercent"`
	InterruptionRisk string  `json:"interruptionRisk"`
	WorkloadType     string  `json:"workloadType"`
	Eligible         bool    `json:"eligible"`
	Reason           string  `json:"reason"`
}

type BudgetManager struct {
	cfg     config.BudgetConfig
	pricing config.PricingConfig
}

func NewBudgetManager(cfg config.BudgetConfig, pricing config.PricingConfig) *BudgetManager {
	return &BudgetManager{
		cfg:     cfg,
		pricing: pricing,
	}
}

func (bm *BudgetManager) GetBudget(namespace string) float64 {
	if budget, exists := bm.cfg.Namespaces[namespace]; exists {
		return budget
	}
	return bm.cfg.DefaultMonthlyBudget
}

func (bm *BudgetManager) CheckBudgets(namespaceCosts []NamespaceCost) []BudgetAlert {
	now := time.Now()
	daysInMonth := 30
	dayOfMonth := now.Day()
	daysRemaining := daysInMonth - dayOfMonth
	usageRatio := float64(dayOfMonth) / float64(daysInMonth)

	var alerts []BudgetAlert

	for _, nc := range namespaceCosts {
		budget := bm.GetBudget(nc.Namespace)
		dailyCost := nc.Cost.Total / 24
		currentMonthlyCost := dailyCost * float64(dayOfMonth)
		projectedCost := dailyCost * float64(daysInMonth)
		percentage := currentMonthlyCost / budget

		level := "normal"
		message := "Within budget"

		if percentage >= bm.cfg.CriticalThreshold {
			level = "critical"
			message = "CRITICAL: Budget exceeded!"
		} else if percentage >= bm.cfg.AlertThreshold {
			level = "warning"
			message = "WARNING: Approaching budget limit"
		} else if projectedCost > budget {
			level = "warning"
			message = "WARNING: Projected to exceed budget at current rate"
		}

		if level != "normal" {
			alerts = append(alerts, BudgetAlert{
				Namespace:     nc.Namespace,
				CurrentCost:   currentMonthlyCost,
				Budget:        budget,
				Percentage:    percentage,
				Level:         level,
				Message:       message,
				DaysRemaining: daysRemaining,
				ProjectedCost: projectedCost,
			})
		}
	}

	sort.Slice(alerts, func(i, j int) bool {
		levelOrder := map[string]int{"critical": 3, "warning": 2, "normal": 1}
		if levelOrder[alerts[i].Level] != levelOrder[alerts[j].Level] {
			return levelOrder[alerts[i].Level] > levelOrder[alerts[j].Level]
		}
		return alerts[i].Percentage > alerts[j].Percentage
	})

	return alerts
}

func (bm *BudgetManager) CalculatePriceComparison(cpuCores, memoryGB float64) []PriceComparison {
	hoursPerMonth := 24 * 30

	onDemand := PriceComparison{
		Scenario:         "On-Demand",
		MonthlyCPUCost:   cpuCores * bm.pricing.OnDemand.CPUPerCoreHour * hoursPerMonth,
		MonthlyMemoryCost: memoryGB * bm.pricing.OnDemand.MemoryPerGBHour * hoursPerMonth,
	}
	onDemand.TotalMonthlyCost = onDemand.MonthlyCPUCost + onDemand.MonthlyMemoryCost

	reserved := PriceComparison{
		Scenario:         "Reserved Instances",
		MonthlyCPUCost:   cpuCores * bm.pricing.Reserved.CPUPerCoreHour * hoursPerMonth,
		MonthlyMemoryCost: memoryGB * bm.pricing.Reserved.MemoryPerGBHour * hoursPerMonth,
		UpfrontCost:      cpuCores*bm.pricing.Reserved.UpfrontFeePerCore + memoryGB*bm.pricing.Reserved.UpfrontFeePerGB,
	}
	reserved.TotalMonthlyCost = reserved.MonthlyCPUCost + reserved.MonthlyMemoryCost
	reserved.AnnualSavings = (onDemand.TotalMonthlyCost - reserved.TotalMonthlyCost) * 12
	reserved.SavingsPercent = ((onDemand.TotalMonthlyCost - reserved.TotalMonthlyCost) / onDemand.TotalMonthlyCost) * 100
	reserved.BreakEvenMonths = reserved.UpfrontCost / (onDemand.TotalMonthlyCost - reserved.TotalMonthlyCost)

	spot := PriceComparison{
		Scenario:         "Spot Instances",
		MonthlyCPUCost:   cpuCores * bm.pricing.Spot.CPUPerCoreHour * hoursPerMonth,
		MonthlyMemoryCost: memoryGB * bm.pricing.Spot.MemoryPerGBHour * hoursPerMonth,
	}
	spot.TotalMonthlyCost = spot.MonthlyCPUCost + spot.MonthlyMemoryCost
	spot.AnnualSavings = (onDemand.TotalMonthlyCost - spot.TotalMonthlyCost) * 12
	spot.SavingsPercent = ((onDemand.TotalMonthlyCost - spot.TotalMonthlyCost) / onDemand.TotalMonthlyCost) * 100

	return []PriceComparison{onDemand, reserved, spot}
}

func (bm *BudgetManager) GetSpotRecommendations(namespaceCosts []NamespaceCost) []SpotRecommendation {
	var recommendations []SpotRecommendation

	for _, nc := range namespaceCosts {
		cpuCores := nc.ResourceUsage.CPURequestCores
		memoryGB := nc.ResourceUsage.MemoryRequestGB
		hoursPerMonth := 24 * 30

		onDemandMonthly := cpuCores*bm.pricing.OnDemand.CPUPerCoreHour*hoursPerMonth +
			memoryGB*bm.pricing.OnDemand.MemoryPerGBHour*hoursPerMonth
		spotMonthly := cpuCores*bm.pricing.Spot.CPUPerCoreHour*hoursPerMonth +
			memoryGB*bm.pricing.Spot.MemoryPerGBHour*hoursPerMonth
		monthlySavings := onDemandMonthly - spotMonthly
		savingsPercent := (monthlySavings / onDemandMonthly) * 100

		eligible := true
		reason := "Good candidate for Spot instances"
		interruptionRisk := "low"
		workloadType := "unknown"

		if env, ok := nc.Labels["environment"]; ok {
			if env == "production" {
				eligible = false
				reason = "Production workloads are not recommended for Spot instances"
				interruptionRisk = "high"
				workloadType = "production"
			} else if env == "staging" {
				workloadType = "staging"
				interruptionRisk = "medium"
			} else {
				workloadType = env
			}
		}

		if savingsPercent < bm.pricing.Spot.DiscountThreshold*100 {
			eligible = false
			reason = "Savings percentage too low to justify Spot instances"
		}

		recommendations = append(recommendations, SpotRecommendation{
			Namespace:       nc.Namespace,
			CPUCores:        cpuCores,
			MemoryGB:        memoryGB,
			OnDemandMonthly: onDemandMonthly,
			SpotMonthly:     spotMonthly,
			MonthlySavings:  monthlySavings,
			SavingsPercent:  savingsPercent,
			InterruptionRisk: interruptionRisk,
			WorkloadType:    workloadType,
			Eligible:        eligible,
			Reason:          reason,
		})
	}

	sort.Slice(recommendations, func(i, j int) bool {
		if recommendations[i].Eligible != recommendations[j].Eligible {
			return recommendations[i].Eligible
		}
		return recommendations[i].MonthlySavings > recommendations[j].MonthlySavings
	})

	return recommendations
}

func (bm *BudgetManager) SimulateReservedPurchase(cpuCores, memoryGB float64, existingOnDemandCost float64) PriceComparison {
	comparisons := bm.CalculatePriceComparison(cpuCores, memoryGB)
	for _, c := range comparisons {
		if c.Scenario == "Reserved Instances" {
			return c
		}
	}
	return PriceComparison{}
}

package cost

import (
	"fmt"
	"time"

	"github.com/coldstart-optimizer/coldstart/internal/model"
)

type PricingModel struct {
	Currency        string
	CPUPerMs        float64
	MemoryMBPerMs   float64
	PullPerGB       float64
	IOPerGB         float64
	LatencyPenalty  float64
	InvocationsPerMonth int64
}

func DefaultPricing() PricingModel {
	return PricingModel{
		Currency:             "CNY",
		CPUPerMs:             0.000012,
		MemoryMBPerMs:        0.000002,
		PullPerGB:            0.05,
		IOPerGB:              0.001,
		LatencyPenalty:       0.00001,
		InvocationsPerMonth:  1000000,
	}
}

func CheapPricing() PricingModel {
	p := DefaultPricing()
	p.Currency = "USD"
	p.CPUPerMs = 0.0000017
	p.MemoryMBPerMs = 0.0000003
	p.PullPerGB = 0.008
	p.IOPerGB = 0.00015
	p.LatencyPenalty = 0.0000015
	return p
}

type Analyzer struct {
	pricing PricingModel
}

func NewAnalyzer(pricing PricingModel) *Analyzer {
	return &Analyzer{pricing: pricing}
}

func (a *Analyzer) Analyze(profile model.ColdStartProfile) *model.CostAnalysis {
	resources := profile.Resources
	totalDur := profile.Total
	totalSeconds := totalDur.Seconds()

	cpuCost := resources.CPUMillis * totalSeconds * a.pricing.CPUPerMs * 1000
	memCost := float64(resources.MemoryMB) * totalSeconds * a.pricing.MemoryMBPerMs
	pullCost := float64(resources.NetRxKB)/1024/1024 * a.pricing.PullPerGB
	ioCost := (float64(resources.DiskReadKB+resources.DiskWriteKB)) / 1024 / 1024 * a.pricing.IOPerGB
	latencyPenalty := totalDur.Seconds() * a.pricing.LatencyPenalty * 1000
	total := cpuCost + memCost + pullCost + ioCost + latencyPenalty

	warmCPUMillis := resources.CPUMillis * 0.3
	warmMemMB := resources.MemoryMB
	warmSeconds := totalDur.Seconds() * 0.15
	warmCPU := warmCPUMillis * warmSeconds * a.pricing.CPUPerMs * 1000
	warmMem := float64(warmMemMB) * warmSeconds * a.pricing.MemoryMBPerMs
	warmPull := 0.0
	warmIO := ioCost * 0.1
	warmLatency := warmSeconds * a.pricing.LatencyPenalty * 1000
	warmTotal := warmCPU + warmMem + warmPull + warmIO + warmLatency

	cold := model.CostBreakdown{
		Currency:       a.pricing.Currency,
		TotalCost:      total,
		CPUCost:        cpuCost,
		MemoryCost:     memCost,
		PullCost:       pullCost,
		IOCost:         ioCost,
		LatencyPenalty: latencyPenalty,
		CompareWarm:    warmTotal,
	}

	warm := model.CostBreakdown{
		Currency:       a.pricing.Currency,
		TotalCost:      warmTotal,
		CPUCost:        warmCPU,
		MemoryCost:     warmMem,
		PullCost:       warmPull,
		IOCost:         warmIO,
		LatencyPenalty: warmLatency,
		CompareWarm:    0,
	}

	delta := model.CostBreakdown{
		Currency:       a.pricing.Currency,
		TotalCost:      total - warmTotal,
		CPUCost:        cpuCost - warmCPU,
		MemoryCost:     memCost - warmMem,
		PullCost:       pullCost - warmPull,
		IOCost:         ioCost - warmIO,
		LatencyPenalty: latencyPenalty - warmLatency,
		CompareWarm:    0,
	}

	perInvoc := total
	perMonth := perInvoc * float64(a.pricing.InvocationsPerMonth)
	savings := (total - warmTotal) * float64(a.pricing.InvocationsPerMonth)

	return &model.CostAnalysis{
		ColdStart:           cold,
		WarmStart:           warm,
		Delta:               delta,
		PerInvocations:      perInvoc,
		PerMonthEst:         perMonth,
		OptimizationSavings: savings,
		Currency:            a.pricing.Currency,
	}
}

func FormatCost(v float64, currency string) string {
	switch {
	case v >= 1000:
		return fmt.Sprintf("%s%.2f", currencySymbol(currency), v)
	case v >= 1:
		return fmt.Sprintf("%s%.4f", currencySymbol(currency), v)
	case v >= 0.01:
		return fmt.Sprintf("%s%.6f", currencySymbol(currency), v)
	default:
		return fmt.Sprintf("%s%.8f", currencySymbol(currency), v)
	}
}

func currencySymbol(c string) string {
	switch c {
	case "CNY", "RMB":
		return "¥"
	case "USD":
		return "$"
	case "EUR":
		return "€"
	case "GBP":
		return "£"
	case "JPY":
		return "¥"
	default:
		return c + " "
	}
}

type CostSummary struct {
	PerInvocation   string
	PerMonth        string
	WarmSavings     string
	SavingsPercent  float64
}

func (a *Analyzer) Summarize(analysis *model.CostAnalysis) CostSummary {
	savingsPct := 0.0
	if analysis.ColdStart.TotalCost > 0 {
		savingsPct = (analysis.ColdStart.TotalCost - analysis.WarmStart.TotalCost) / analysis.ColdStart.TotalCost * 100
	}
	return CostSummary{
		PerInvocation:  FormatCost(analysis.PerInvocations, analysis.Currency),
		PerMonth:       FormatCost(analysis.PerMonthEst, analysis.Currency),
		WarmSavings:    FormatCost(analysis.OptimizationSavings, analysis.Currency),
		SavingsPercent: savingsPct,
	}
}

func DurationToCost(dur time.Duration, cpuMillis, memMB float64, pricing PricingModel) float64 {
	seconds := dur.Seconds()
	return cpuMillis*seconds*pricing.CPUPerMs*1000 +
		memMB*seconds*pricing.MemoryMBPerMs
}

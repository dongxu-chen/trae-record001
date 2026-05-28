package report

import (
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"strings"
	"text/tabwriter"
	"time"

	"github.com/coldstart-optimizer/coldstart/internal/cost"
	"github.com/coldstart-optimizer/coldstart/internal/model"
)

type Renderer struct {
	Output io.Writer
	Format string
}

func NewRenderer(w io.Writer, format string) *Renderer {
	if format == "" {
		format = "text"
	}
	return &Renderer{Output: w, Format: format}
}

func (r *Renderer) Render(report *model.ColdStartReport) error {
	switch r.Format {
	case "json":
		return r.renderJSON(report)
	default:
		return r.renderText(report)
	}
}

func (r *Renderer) renderJSON(report *model.ColdStartReport) error {
	enc := json.NewEncoder(r.Output)
	enc.SetIndent("", "  ")
	return enc.Encode(report)
}

func (r *Renderer) renderText(report *model.ColdStartReport) error {
	out := r.Output
	p := report.Profile

	fmt.Fprintln(out, "==================================================")
	fmt.Fprintln(out, "       SERVERLESS COLD-START DECOMPOSE REPORT    ")
	fmt.Fprintln(out, "==================================================")
	fmt.Fprintf(out, "Function     : %s\n", p.Function)
	fmt.Fprintf(out, "Runtime      : %s\n", p.Runtime)
	fmt.Fprintf(out, "Container ID : %s\n", p.ContainerID)
	fmt.Fprintf(out, "Triggered At : %s\n", p.TriggeredAt.Format(time.RFC3339Nano))
	fmt.Fprintf(out, "Ready At     : %s\n", p.ReadyAt.Format(time.RFC3339Nano))
	fmt.Fprintf(out, "Total        : %v\n", p.Total)
	fmt.Fprintln(out, "--------------------------------------------------")
	fmt.Fprintln(out, "PHASE BREAKDOWN")
	fmt.Fprintln(out, "--------------------------------------------------")

	phases := make([]model.PhaseRecord, len(p.Phases))
	copy(phases, p.Phases)
	sort.SliceStable(phases, func(i, k int) bool { return phases[i].Start.Before(phases[k].Start) })

	tw := tabwriter.NewWriter(out, 0, 2, 2, ' ', 0)
	fmt.Fprintln(tw, "PHASE\tSTART\tDURATION\tSOURCE\tDETAIL")
	for _, ph := range phases {
		bar := barFor(ph.Duration, p.Total)
		fmt.Fprintf(tw, "%s\t%s\t%v\t%s\t%s %s\n",
			ph.Phase,
			ph.Start.Format("15:04:05.000"),
			ph.Duration,
			ph.Source,
			bar,
			ph.Detail,
		)
	}
	tw.Flush()

	fmt.Fprintln(out, "--------------------------------------------------")
	fmt.Fprintln(out, "OPTIMIZATION SUGGESTIONS")
	fmt.Fprintln(out, "--------------------------------------------------")

	if len(report.Suggestions) == 0 {
		fmt.Fprintln(out, "No issues detected; current cold-start path is healthy.")
	} else {
		for _, s := range report.Suggestions {
			stars := strings.Repeat("*", 7-s.Priority)
			fmt.Fprintf(out, "[%s] %s %s\n", s.Kind, stars, s.Description)
			fmt.Fprintf(out, "  target_phase=%s  expected_gain=%v  confidence=%.0f%%\n",
				s.TargetPhase, s.ExpectedGain, s.Confidence*100)
		}
	}

	fmt.Fprintln(out, "--------------------------------------------------")
	fmt.Fprintln(out, "RESOURCE USAGE")
	fmt.Fprintln(out, "--------------------------------------------------")
	fmt.Fprintf(out, "CPU(millis) = %.1f   Memory(MB) = %d\n", p.Resources.CPUMillis, p.Resources.MemoryMB)
	fmt.Fprintf(out, "Disk read(KB) = %d   Disk write(KB) = %d\n", p.Resources.DiskReadKB, p.Resources.DiskWriteKB)
	fmt.Fprintf(out, "Net  RX(KB)   = %d   Net TX(KB)    = %d\n", p.Resources.NetRxKB, p.Resources.NetTxKB)

	if report.CostAnalysis != nil {
		r.renderCostText(out, report.CostAnalysis)
	}

	fmt.Fprintln(out, "==================================================")
	fmt.Fprintf(out, "Generated at %s\n", report.GeneratedAt.Format(time.RFC3339))
	return nil
}

func (r *Renderer) renderCostText(out io.Writer, ca *model.CostAnalysis) {
	fmt.Fprintln(out, "--------------------------------------------------")
	fmt.Fprintln(out, "COST ANALYSIS")
	fmt.Fprintln(out, "--------------------------------------------------")
	fmt.Fprintf(out, "Currency     : %s\n", ca.Currency)
	fmt.Fprintf(out, "Per Invocation: %s\n", cost.FormatCost(ca.PerInvocations, ca.Currency))
	fmt.Fprintf(out, "Per Month Est : %s\n", cost.FormatCost(ca.PerMonthEst, ca.Currency))
	fmt.Fprintf(out, "Warm Savings  : %s\n", cost.FormatCost(ca.OptimizationSavings, ca.Currency))

	tw := tabwriter.NewWriter(out, 0, 2, 2, ' ', 0)
	fmt.Fprintln(tw, "ITEM\tCOLD START\tWARM START\tDELTA")
	fmt.Fprintf(tw, "CPU\t%s\t%s\t%s\n",
		cost.FormatCost(ca.ColdStart.CPUCost, ca.Currency),
		cost.FormatCost(ca.WarmStart.CPUCost, ca.Currency),
		cost.FormatCost(ca.Delta.CPUCost, ca.Currency))
	fmt.Fprintf(tw, "Memory\t%s\t%s\t%s\n",
		cost.FormatCost(ca.ColdStart.MemoryCost, ca.Currency),
		cost.FormatCost(ca.WarmStart.MemoryCost, ca.Currency),
		cost.FormatCost(ca.Delta.MemoryCost, ca.Currency))
	fmt.Fprintf(tw, "Pull\t%s\t%s\t%s\n",
		cost.FormatCost(ca.ColdStart.PullCost, ca.Currency),
		cost.FormatCost(ca.WarmStart.PullCost, ca.Currency),
		cost.FormatCost(ca.Delta.PullCost, ca.Currency))
	fmt.Fprintf(tw, "I/O\t%s\t%s\t%s\n",
		cost.FormatCost(ca.ColdStart.IOCost, ca.Currency),
		cost.FormatCost(ca.WarmStart.IOCost, ca.Currency),
		cost.FormatCost(ca.Delta.IOCost, ca.Currency))
	fmt.Fprintf(tw, "Latency Penalty\t%s\t%s\t%s\n",
		cost.FormatCost(ca.ColdStart.LatencyPenalty, ca.Currency),
		cost.FormatCost(ca.WarmStart.LatencyPenalty, ca.Currency),
		cost.FormatCost(ca.Delta.LatencyPenalty, ca.Currency))
	fmt.Fprintf(tw, "TOTAL\t%s\t%s\t%s\n",
		cost.FormatCost(ca.ColdStart.TotalCost, ca.Currency),
		cost.FormatCost(ca.WarmStart.TotalCost, ca.Currency),
		cost.FormatCost(ca.Delta.TotalCost, ca.Currency))
	tw.Flush()
}

func barFor(d, total time.Duration) string {
	if total <= 0 {
		return ""
	}
	ratio := float64(d) / float64(total)
	width := 20
	n := int(float64(width) * ratio)
	if n < 0 {
		n = 0
	}
	if n > width {
		n = width
	}
	return strings.Repeat("#", n) + strings.Repeat(".", width-n)
}

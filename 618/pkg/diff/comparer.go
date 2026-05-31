package diff

import (
	"fmt"
	"strings"
)

type DiffLine struct {
	Type    string 
	Content string
	LineNo  int
}

type DiffResult struct {
	Lines       []DiffLine
	AddedCount  int
	RemovedCount int
	ChangedCount int
}

func Compare(oldContent, newContent string) *DiffResult {
	oldLines := strings.Split(oldContent, "\n")
	newLines := strings.Split(newContent, "\n")

	result := &DiffResult{
		Lines: make([]DiffLine, 0),
	}

	lcs := computeLCS(oldLines, newLines)

	i, j := 0, 0
	for _, line := range lcs {
		for i < len(oldLines) && oldLines[i] != line {
			result.Lines = append(result.Lines, DiffLine{
				Type:    "removed",
				Content: oldLines[i],
				LineNo:  i + 1,
			})
			result.RemovedCount++
			i++
		}
		for j < len(newLines) && newLines[j] != line {
			result.Lines = append(result.Lines, DiffLine{
				Type:    "added",
				Content: newLines[j],
				LineNo:  j + 1,
			})
			result.AddedCount++
			j++
		}
		result.Lines = append(result.Lines, DiffLine{
			Type:    "unchanged",
			Content: line,
			LineNo:  j + 1,
		})
		i++
		j++
	}

	for i < len(oldLines) {
		result.Lines = append(result.Lines, DiffLine{
			Type:    "removed",
			Content: oldLines[i],
			LineNo:  i + 1,
		})
		result.RemovedCount++
		i++
	}

	for j < len(newLines) {
		result.Lines = append(result.Lines, DiffLine{
			Type:    "added",
			Content: newLines[j],
			LineNo:  j + 1,
		})
		result.AddedCount++
		j++
	}

	result.ChangedCount = result.AddedCount + result.RemovedCount

	return result
}

func computeLCS(a, b []string) []string {
	m, n := len(a), len(b)
	dp := make([][]int, m+1)
	for i := range dp {
		dp[i] = make([]int, n+1)
	}

	for i := 1; i <= m; i++ {
		for j := 1; j <= n; j++ {
			if a[i-1] == b[j-1] {
				dp[i][j] = dp[i-1][j-1] + 1
			} else {
				dp[i][j] = max(dp[i-1][j], dp[i][j-1])
			}
		}
	}

	var lcs []string
	i, j := m, n
	for i > 0 && j > 0 {
		if a[i-1] == b[j-1] {
			lcs = append([]string{a[i-1]}, lcs...)
			i--
			j--
		} else if dp[i-1][j] > dp[i][j-1] {
			i--
		} else {
			j--
		}
	}

	return lcs
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func (r *DiffResult) GetSummary() string {
	return fmt.Sprintf("+%d -%d 共%d处变更", r.AddedCount, r.RemovedCount, r.ChangedCount)
}

func (r *DiffResult) GetHTML() string {
	var sb strings.Builder
	for _, line := range r.Lines {
		switch line.Type {
		case "added":
			sb.WriteString(fmt.Sprintf(`<div class="diff-added">+ %s</div>`, escapeHTML(line.Content)))
		case "removed":
			sb.WriteString(fmt.Sprintf(`<div class="diff-removed">- %s</div>`, escapeHTML(line.Content)))
		default:
			sb.WriteString(fmt.Sprintf(`<div class="diff-unchanged">  %s</div>`, escapeHTML(line.Content)))
		}
	}
	return sb.String()
}

func escapeHTML(s string) string {
	s = strings.ReplaceAll(s, "&", "&amp;")
	s = strings.ReplaceAll(s, "<", "&lt;")
	s = strings.ReplaceAll(s, ">", "&gt;")
	return s
}

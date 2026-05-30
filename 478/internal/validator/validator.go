package validator

import (
	"fmt"
	"nginx-lint/internal/expander"
	"nginx-lint/internal/fixer"
	"nginx-lint/internal/includeresolver"
	"nginx-lint/internal/model"
	"nginx-lint/internal/parser"
	"nginx-lint/internal/perf"
	"nginx-lint/internal/rules"
	"nginx-lint/internal/security"
	"os"
	"path/filepath"
	"strings"
)

type LintResult struct {
	FilePath     string
	Errors       []*model.LintError
	Nodes        []*model.Node
	Fixes        []*fixer.FixSuggestion
	PerfReport   *perf.PerfReport
}

type Validator struct {
	ResolveIncludes bool
	CheckVariables  bool
	CheckDirectives bool
	CheckSecurity   bool
	CheckPerf       bool
	StrictMode      bool
	ShowInfo        bool
}

func NewValidator() *Validator {
	return &Validator{
		ResolveIncludes: true,
		CheckVariables:  true,
		CheckDirectives: true,
		CheckSecurity:   true,
		CheckPerf:       true,
		StrictMode:      false,
		ShowInfo:        false,
	}
}

func (v *Validator) ValidateFile(filePath string) (*LintResult, error) {
	absPath, err := filepath.Abs(filePath)
	if err != nil {
		return nil, fmt.Errorf("获取绝对路径失败: %w", err)
	}

	content, err := os.ReadFile(absPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("文件不存在: %s", absPath)
		}
		return nil, fmt.Errorf("读取文件失败: %w", err)
	}

	return v.ValidateContent(string(content), absPath)
}

func (v *Validator) ValidateContent(content, filePath string) (*LintResult, error) {
	result := &LintResult{
		FilePath: filePath,
		Errors:   []*model.LintError{},
	}

	nodes, parseErrors := parser.ParseFile(content, filePath)
	result.Errors = append(result.Errors, parseErrors...)
	result.Nodes = nodes

	if len(parseErrors) > 0 {
		return result, nil
	}

	ctx := model.NewConfigContext(filePath)

	if v.ResolveIncludes {
		resolvedNodes, includeErrors := includeresolver.ResolveIncludes(nodes, filePath)
		result.Errors = append(result.Errors, includeErrors...)
		nodes = resolvedNodes
		result.Nodes = nodes
	}

	if v.CheckVariables {
		variableErrors := expander.CheckVariables(nodes, ctx)
		result.Errors = append(result.Errors, variableErrors...)
	}

	if v.CheckDirectives {
		var directiveErrors []*model.LintError
		if v.StrictMode {
			directiveErrors = rules.ValidateDirectivesStrict(nodes)
		} else {
			directiveErrors = rules.ValidateDirectives(nodes)
		}
		for _, e := range directiveErrors {
			if e.Severity == model.SeverityInfo && !v.ShowInfo {
				continue
			}
			result.Errors = append(result.Errors, e)
		}
	}

	if v.CheckSecurity {
		securityErrors := security.CheckSecurity(nodes)
		result.Errors = append(result.Errors, securityErrors...)
	}

	if v.CheckPerf {
		result.PerfReport = perf.Analyze(nodes)
		if result.PerfReport != nil {
			result.Errors = append(result.Errors, result.PerfReport.Warnings...)
		}
	}

	result.Fixes = fixer.GenerateFixes(result.Errors)

	return result, nil
}

func (v *Validator) ValidateFiles(filePaths []string) ([]*LintResult, error) {
	var results []*LintResult

	for _, path := range filePaths {
		result, err := v.ValidateFile(path)
		if err != nil {
			results = append(results, &LintResult{
				FilePath: path,
				Errors: []*model.LintError{
					{
						Pos: model.Position{
							File: path,
							Line: 1,
						},
						Severity:   model.SeverityError,
						RuleID:     "ERR_FILE_READ",
						Message:    err.Error(),
						Suggestion: "检查文件路径和权限",
					},
				},
			})
			continue
		}
		results = append(results, result)
	}

	return results, nil
}

func (v *Validator) ValidateDirectory(dirPath string, recursive bool) ([]*LintResult, error) {
	var files []string

	walkFn := func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			if !recursive && path != dirPath {
				return filepath.SkipDir
			}
			return nil
		}
		if isNginxConfigFile(path) {
			files = append(files, path)
		}
		return nil
	}

	err := filepath.Walk(dirPath, walkFn)
	if err != nil {
		return nil, fmt.Errorf("遍历目录失败: %w", err)
	}

	return v.ValidateFiles(files)
}

func isNginxConfigFile(path string) bool {
	ext := strings.ToLower(filepath.Ext(path))
	if ext == ".conf" {
		return true
	}
	base := strings.ToLower(filepath.Base(path))
	if base == "nginx.conf" {
		return true
	}
	return false
}

func (r *LintResult) HasErrors() bool {
	for _, e := range r.Errors {
		if e.Severity == model.SeverityError {
			return true
		}
	}
	return false
}

func (r *LintResult) HasWarnings() bool {
	for _, e := range r.Errors {
		if e.Severity == model.SeverityWarning {
			return true
		}
	}
	return false
}

func (r *LintResult) ErrorCount() int {
	count := 0
	for _, e := range r.Errors {
		if e.Severity == model.SeverityError {
			count++
		}
	}
	return count
}

func (r *LintResult) WarningCount() int {
	count := 0
	for _, e := range r.Errors {
		if e.Severity == model.SeverityWarning {
			count++
		}
	}
	return count
}

func FormatErrors(errors []*model.LintError, format string) string {
	var sb strings.Builder

	for _, err := range errors {
		sb.WriteString(FormatError(err, format))
		sb.WriteString("\n")
	}

	return sb.String()
}

func FormatError(err *model.LintError, format string) string {
	severityStr := "INFO"
	switch err.Severity {
	case model.SeverityError:
		severityStr = "ERROR"
	case model.SeverityWarning:
		severityStr = "WARNING"
	}

	switch strings.ToLower(format) {
	case "json":
		return fmt.Sprintf(`{"file":"%s","line":%d,"column":%d,"severity":"%s","rule":"%s","message":"%s","suggestion":"%s"}`,
			escapeJSON(err.Pos.File), err.Pos.Line, err.Pos.Column,
			severityStr, err.RuleID, escapeJSON(err.Message), escapeJSON(err.Suggestion))
	case "compact":
		return fmt.Sprintf("%s:%d:%d: %s: %s [%s]",
			err.Pos.File, err.Pos.Line, err.Pos.Column,
			severityStr, err.Message, err.RuleID)
	default:
		var sb strings.Builder
		sb.WriteString(fmt.Sprintf("%s:%d:%d\n", err.Pos.File, err.Pos.Line, err.Pos.Column))
		sb.WriteString(fmt.Sprintf("  %s: %s\n", severityStr, err.Message))
		sb.WriteString(fmt.Sprintf("  规则: %s\n", err.RuleID))
		if err.Suggestion != "" {
			sb.WriteString(fmt.Sprintf("  建议: %s\n", err.Suggestion))
		}
		if err.RelatedPosition != nil {
			sb.WriteString(fmt.Sprintf("  相关位置: %s:%d\n",
				err.RelatedPosition.File, err.RelatedPosition.Line))
		}
		return sb.String()
	}
}

func escapeJSON(s string) string {
	s = strings.ReplaceAll(s, "\\", "\\\\")
	s = strings.ReplaceAll(s, "\"", "\\\"")
	s = strings.ReplaceAll(s, "\n", "\\n")
	s = strings.ReplaceAll(s, "\r", "\\r")
	s = strings.ReplaceAll(s, "\t", "\\t")
	return s
}

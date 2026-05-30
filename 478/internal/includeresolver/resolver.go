package includeresolver

import (
	"fmt"
	"nginx-lint/internal/model"
	"nginx-lint/internal/parser"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

const maxIncludeDepth = 32

type includeChainEntry struct {
	File string
	Line int
}

type IncludeResolver struct {
	basePath     string
	parsedFiles  map[string]bool
	errors       []*model.LintError
	includeChain []includeChainEntry
	currentDepth int
}

func NewIncludeResolver(basePath string) *IncludeResolver {
	return &IncludeResolver{
		basePath:     basePath,
		parsedFiles:  make(map[string]bool),
		errors:       []*model.LintError{},
		includeChain: []includeChainEntry{},
		currentDepth: 0,
	}
}

func (r *IncludeResolver) Errors() []*model.LintError {
	return r.errors
}

func (r *IncludeResolver) Resolve(nodes []*model.Node, parentFile string) []*model.Node {
	var result []*model.Node

	for _, node := range nodes {
		if node.IsInclude {
			included := r.resolveInclude(node, parentFile)
			result = append(result, included...)
		} else {
			if node.Type == model.NodeBlock && len(node.Children) > 0 {
				node.Children = r.Resolve(node.Children, parentFile)
			}
			result = append(result, node)
		}
	}

	return result
}

func (r *IncludeResolver) resolveInclude(node *model.Node, parentFile string) []*model.Node {
	pattern := node.IncludeRef
	absPattern := pattern

	if !filepath.IsAbs(pattern) {
		parentDir := filepath.Dir(parentFile)
		absPattern = filepath.Join(parentDir, pattern)
	}

	if r.currentDepth >= maxIncludeDepth {
		chainStr := r.formatIncludeChain()
		r.addError(node.Pos, "ERR_INCLUDE_DEPTH",
			fmt.Sprintf("include 嵌套深度超过 %d 层限制: %s", maxIncludeDepth, pattern),
			"减少include嵌套层数，或检查是否存在循环引用。引用链: "+chainStr)
		return nil
	}

	r.includeChain = append(r.includeChain, includeChainEntry{
		File: parentFile,
		Line: node.Pos.Line,
	})
	r.currentDepth++
	defer func() {
		r.currentDepth--
		r.includeChain = r.includeChain[:len(r.includeChain)-1]
	}()

	files, err := r.matchFiles(absPattern)
	if err != nil {
		r.addError(node.Pos, "ERR_INCLUDE_GLOB",
			"include 模式匹配失败: "+err.Error(),
			"检查文件路径和通配符是否正确")
		return nil
	}

	if len(files) == 0 {
		r.addError(node.Pos, "WARN_INCLUDE_EMPTY",
			"include 未匹配到任何文件: "+pattern,
			"确认文件存在或路径正确")
		return nil
	}

	var allNodes []*model.Node

	for _, file := range files {
		absFile, _ := filepath.Abs(file)

		if r.parsedFiles[absFile] {
			r.addError(node.Pos, "WARN_INCLUDE_CYCLE",
				"检测到循环include: "+absFile+" (引用链: "+r.formatIncludeChain()+" -> "+absFile+")",
				"检查include引用链，避免循环引用")
			continue
		}

		r.parsedFiles[absFile] = true

		content, err := os.ReadFile(absFile)
		if err != nil {
			if os.IsNotExist(err) {
				r.addError(node.Pos, "ERR_INCLUDE_NOT_FOUND",
					"include 文件不存在: "+absFile,
					"创建文件或修正路径")
			} else {
				r.addError(node.Pos, "ERR_INCLUDE_READ",
					"读取 include 文件失败: "+err.Error(),
					"检查文件权限")
			}
			continue
		}

		parsedNodes, parseErrors := parser.ParseFile(string(content), absFile)
		r.errors = append(r.errors, parseErrors...)

		resolved := r.Resolve(parsedNodes, absFile)
		allNodes = append(allNodes, resolved...)
	}

	return allNodes
}

func (r *IncludeResolver) formatIncludeChain() string {
	var parts []string
	for _, entry := range r.includeChain {
		parts = append(parts, fmt.Sprintf("%s:%d", entry.File, entry.Line))
	}
	return strings.Join(parts, " -> ")
}

func (r *IncludeResolver) matchFiles(pattern string) ([]string, error) {
	if !containsGlob(pattern) {
		if _, err := os.Stat(pattern); err == nil {
			return []string{pattern}, nil
		}
		return nil, nil
	}

	dir := filepath.Dir(pattern)
	filePattern := filepath.Base(pattern)

	if _, err := os.Stat(dir); os.IsNotExist(err) {
		return nil, err
	}

	regex := globToRegex(filePattern)

	files, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	var matches []string
	for _, f := range files {
		if f.IsDir() {
			continue
		}
		if regex.MatchString(f.Name()) {
			matches = append(matches, filepath.Join(dir, f.Name()))
		}
	}

	return matches, nil
}

func containsGlob(pattern string) bool {
	return strings.ContainsAny(pattern, "*?[")
}

func globToRegex(pattern string) *regexp.Regexp {
	var sb strings.Builder
	sb.WriteRune('^')

	escaping := false
	for _, ch := range pattern {
		if escaping {
			sb.WriteRune(ch)
			escaping = false
			continue
		}

		switch ch {
		case '\\':
			sb.WriteRune('\\')
			escaping = true
		case '*':
			sb.WriteString(".*")
		case '?':
			sb.WriteRune('.')
		case '.':
			sb.WriteString("\\.")
		case '+':
			sb.WriteString("\\+")
		case '(':
			sb.WriteString("\\(")
		case ')':
			sb.WriteString("\\)")
		case '|':
			sb.WriteString("\\|")
		case '^':
			sb.WriteString("\\^")
		case '$':
			sb.WriteString("\\$")
		case '[':
			sb.WriteRune('[')
		case ']':
			sb.WriteRune(']')
		default:
			sb.WriteRune(ch)
		}
	}

	sb.WriteRune('$')
	return regexp.MustCompile(sb.String())
}

func (r *IncludeResolver) addError(pos model.Position, ruleID, msg, suggestion string) {
	sev := model.SeverityError
	if strings.HasPrefix(ruleID, "WARN_") {
		sev = model.SeverityWarning
	}
	r.errors = append(r.errors, &model.LintError{
		Pos:        pos,
		Severity:   sev,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func ResolveIncludes(nodes []*model.Node, baseFile string) ([]*model.Node, []*model.LintError) {
	basePath := filepath.Dir(baseFile)
	resolver := NewIncludeResolver(basePath)
	absBase, _ := filepath.Abs(baseFile)
	resolver.parsedFiles[absBase] = true
	resolved := resolver.Resolve(nodes, baseFile)
	return resolved, resolver.Errors()
}

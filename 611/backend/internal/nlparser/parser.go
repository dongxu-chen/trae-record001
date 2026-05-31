package nlparser

import (
	"cloud-tag-compliance/internal/cloud"
	"cloud-tag-compliance/internal/rules"
	"fmt"
	"regexp"
	"strings"
	"unicode"
)

type ParseResult struct {
	Success       bool        `json:"success"`
	Rule          *rules.Rule `json:"rule,omitempty"`
	OriginalText  string      `json:"originalText"`
	Interpretation string     `json:"interpretation"`
	Confidence    float64     `json:"confidence"`
	Warnings      []string    `json:"warnings,omitempty"`
	Suggestions   []string    `json:"suggestions,omitempty"`
}

type PatternMatcher struct {
	Pattern     *regexp.Regexp
	RuleType    rules.RuleType
	ExtractFunc func(matches []string) (*rules.Rule, string, float64, []string)
}

type NLParser struct {
	patterns       []PatternMatcher
	severityMap    map[string]string
	resourceTypeMap map[string]cloud.ResourceType
}

func NewNLParser() *NLParser {
	parser := &NLParser{
		severityMap: map[string]string{
			"高": "high", "严重": "high", "critical": "high", "high": "high",
			"中": "medium", "中等": "medium", "medium": "medium", "normal": "medium",
			"低": "low", "轻微": "low", "low": "low", "minor": "low",
		},
		resourceTypeMap: map[string]cloud.ResourceType{
			"ECS": cloud.ECS, "ecs": cloud.ECS, "云服务器": cloud.ECS,
			"RDS": cloud.RDS, "rds": cloud.RDS, "数据库": cloud.RDS,
			"OSS": cloud.OSS, "oss": cloud.OSS, "存储": cloud.OSS, "对象存储": cloud.OSS,
		},
	}

	parser.initPatterns()
	return parser
}

func (p *NLParser) initPatterns() {
	p.patterns = []PatternMatcher{
		{
			Pattern: regexp.MustCompile(`(?i)(?:所有|全部|每个|every|all)\s*(?:资源|云资源|resources?)\s*(?:必须|需要|应当|should|must|have to)\s*(?:有|包含|拥有|设置|有一个|have|contain|include)\s*(?:一个|a|an)?\s*["']?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_\-]*)["']?\s*(?:标签|tag)`),
			RuleType: rules.RequiredTag,
			ExtractFunc: func(matches []string) (*rules.Rule, string, float64, []string) {
				key := matches[1]
				rule := &rules.Rule{
					ID:          fmt.Sprintf("required_%s", strings.ToLower(key)),
					Name:        fmt.Sprintf("Required %s Tag", key),
					Type:        rules.RequiredTag,
					Description: fmt.Sprintf("所有资源必须包含 %s 标签", key),
					Key:         key,
					Severity:    "medium",
					Enabled:     true,
				}
				interpretation := fmt.Sprintf("检测到规则：所有资源必须包含 '%s' 标签", key)
				return rule, interpretation, 0.9, nil
			},
		},
		{
			Pattern: regexp.MustCompile(`(?i)(?:禁止|不允许|不能|don't|do not|should not|must not|never)\s*(?:使用|设置|有|use|have|set)\s*(?:一个|a|an)?\s*["']?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_\-]*)["']?\s*(?:标签|tag)`),
			RuleType: rules.ForbiddenTag,
			ExtractFunc: func(matches []string) (*rules.Rule, string, float64, []string) {
				key := matches[1]
				rule := &rules.Rule{
					ID:          fmt.Sprintf("forbidden_%s", strings.ToLower(key)),
					Name:        fmt.Sprintf("Forbidden %s Tag", key),
					Type:        rules.ForbiddenTag,
					Description: fmt.Sprintf("禁止使用 %s 标签", key),
					Key:         key,
					Severity:    "low",
					Enabled:     true,
				}
				interpretation := fmt.Sprintf("检测到规则：禁止使用 '%s' 标签", key)
				return rule, interpretation, 0.9, nil
			},
		},
		{
			Pattern: regexp.MustCompile(`(?i)(?:["']?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_\-]*)["']?\s*(?:标签|tag)\s*(?:的值|value)?\s*(?:必须|应当|should|must)\s*(?:为|是|be|equal to|match)\s*)["']?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_\-]*)["']?`),
			RuleType: rules.TagValueInList,
			ExtractFunc: func(matches []string) (*rules.Rule, string, float64, []string) {
				key := matches[1]
				value := matches[2]
				rule := &rules.Rule{
					ID:          fmt.Sprintf("value_%s", strings.ToLower(key)),
					Name:        fmt.Sprintf("%s Tag Value Check", key),
					Type:        rules.TagValueInList,
					Description: fmt.Sprintf("%s 标签的值必须为 %s", key, value),
					Key:         key,
					Values:      []string{value},
					Severity:    "medium",
					Enabled:     true,
				}
				interpretation := fmt.Sprintf("检测到规则：'%s' 标签的值必须为 '%s'", key, value)
				return rule, interpretation, 0.8, nil
			},
		},
		{
			Pattern: regexp.MustCompile(`(?i)(?:["']?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_\-]*)["']?\s*(?:标签|tag)\s*(?:的值|value)?\s*(?:必须|应当|should|must)\s*(?:为|是|be|one of|from)\s*)\[([^\]]+)\]`),
			RuleType: rules.TagValueInList,
			ExtractFunc: func(matches []string) (*rules.Rule, string, float64, []string) {
				key := matches[1]
				valuesStr := matches[2]
				values := parseValueList(valuesStr)
				rule := &rules.Rule{
					ID:          fmt.Sprintf("values_%s", strings.ToLower(key)),
					Name:        fmt.Sprintf("%s Tag Allowed Values", key),
					Type:        rules.TagValueInList,
					Description: fmt.Sprintf("%s 标签的值必须是以下之一: %s", key, strings.Join(values, ", ")),
					Key:         key,
					Values:      values,
					Severity:    "medium",
					Enabled:     true,
				}
				interpretation := fmt.Sprintf("检测到规则：'%s' 标签的值必须是 [%s] 之一", key, strings.Join(values, ", "))
				return rule, interpretation, 0.85, nil
			},
		},
		{
			Pattern: regexp.MustCompile(`(?i)(?:["']?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_\-]*)["']?\s*(?:标签|tag)\s*(?:的值|value)?\s*(?:必须|应当|should|must)\s*(?:匹配|符合|match|follow)\s*(?:正则|正则表达式|pattern|regex)\s*)["']?([^"']+)["']?`),
			RuleType: rules.TagValueRegex,
			ExtractFunc: func(matches []string) (*rules.Rule, string, float64, []string) {
				key := matches[1]
				pattern := matches[2]
				rule := &rules.Rule{
					ID:          fmt.Sprintf("regex_%s", strings.ToLower(key)),
					Name:        fmt.Sprintf("%s Tag Format Check", key),
					Type:        rules.TagValueRegex,
					Description: fmt.Sprintf("%s 标签的值必须匹配正则表达式: %s", key, pattern),
					Key:         key,
					Value:       pattern,
					Severity:    "medium",
					Enabled:     true,
				}
				interpretation := fmt.Sprintf("检测到规则：'%s' 标签的值必须匹配正则表达式 '%s'", key, pattern)
				return rule, interpretation, 0.8, nil
			},
		},
		{
			Pattern: regexp.MustCompile(`(?i)(?:["']?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_\-]*)["']?\s*(?:标签|tag)\s*(?:必须|应当|should|must)\s*(?:区分大小写|大小写敏感|case sensitive))`),
			RuleType: rules.CaseSensitive,
			ExtractFunc: func(matches []string) (*rules.Rule, string, float64, []string) {
				key := matches[1]
				rule := &rules.Rule{
					ID:          fmt.Sprintf("case_%s", strings.ToLower(key)),
					Name:        fmt.Sprintf("%s Tag Case Sensitivity", key),
					Type:        rules.CaseSensitive,
					Description: fmt.Sprintf("%s 标签键必须区分大小写", key),
					Key:         key,
					Severity:    "low",
					Enabled:     true,
				}
				interpretation := fmt.Sprintf("检测到规则：'%s' 标签键必须区分大小写", key)
				return rule, interpretation, 0.9, nil
			},
		},
		{
			Pattern: regexp.MustCompile(`(?i)(?:["']?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_\-]*)["']?\s*(?:标签|tag)\s*(?:只能|仅|only)\s*(?:适用于|用于|apply to|for)\s*)([^。,]+)`),
			RuleType: rules.RequiredTag,
			ExtractFunc: func(matches []string) (*rules.Rule, string, float64, []string) {
				key := matches[1]
				resourceTypesStr := matches[2]
				resourceTypes := parseResourceTypes(resourceTypesStr)
				rule := &rules.Rule{
					ID:            fmt.Sprintf("required_%s", strings.ToLower(key)),
					Name:          fmt.Sprintf("Required %s Tag", key),
					Type:          rules.RequiredTag,
					Description:   fmt.Sprintf("%s 类型的资源必须包含 %s 标签", resourceTypesStr, key),
					Key:           key,
					ResourceTypes: resourceTypes,
					Severity:      "medium",
					Enabled:       true,
				}
				interpretation := fmt.Sprintf("检测到规则：%s 类型的资源必须包含 '%s' 标签", resourceTypesStr, key)
				return rule, interpretation, 0.75, nil
			},
		},
	}
}

func parseValueList(str string) []string {
	str = strings.TrimSpace(str)
	str = strings.Trim(str, "[]")
	parts := strings.Split(str, ",")
	var values []string
	for _, p := range parts {
		p = strings.TrimSpace(p)
		p = strings.Trim(p, "'\"")
		if p != "" {
			values = append(values, p)
		}
	}
	return values
}

func parseResourceTypes(str string) []cloud.ResourceType {
	var types []cloud.ResourceType
	str = strings.ToLower(str)

	keywords := map[string]cloud.ResourceType{
		"ecs":       cloud.ECS,
		"云服务器":    cloud.ECS,
		"服务器":     cloud.ECS,
		"rds":       cloud.RDS,
		"数据库":     cloud.RDS,
		"mysql":     cloud.RDS,
		"postgres":  cloud.RDS,
		"oss":       cloud.OSS,
		"存储":       cloud.OSS,
		"对象存储":    cloud.OSS,
		"bucket":    cloud.OSS,
	}

	for kw, rt := range keywords {
		if strings.Contains(str, kw) {
			exists := false
			for _, t := range types {
				if t == rt {
					exists = true
					break
				}
			}
			if !exists {
				types = append(types, rt)
			}
		}
	}

	return types
}

func (p *NLParser) Parse(text string) ParseResult {
	text = strings.TrimSpace(text)

	if text == "" {
		return ParseResult{
			Success:      false,
			OriginalText: text,
			Interpretation: "输入不能为空",
			Confidence:   0,
			Suggestions: []string{
				"所有资源必须包含 Environment 标签",
				"禁止使用 Owner 标签",
				"Environment 标签的值必须是 [Production, Development, Testing] 之一",
				"CostCenter 标签的值必须匹配正则 ^CC\\d{3}$",
			},
		}
	}

	for _, matcher := range p.patterns {
		matches := matcher.Pattern.FindStringSubmatch(text)
		if matches != nil {
			rule, interpretation, confidence, warnings := matcher.ExtractFunc(matches)

			severity, hasSeverity := p.extractSeverity(text)
			if hasSeverity {
				rule.Severity = severity
				interpretation += fmt.Sprintf("，严重程度为 %s", severity)
			}

			return ParseResult{
				Success:       true,
				Rule:          rule,
				OriginalText:  text,
				Interpretation: interpretation,
				Confidence:    confidence,
				Warnings:      warnings,
			}
		}
	}

	return p.fallbackParse(text)
}

func (p *NLParser) fallbackParse(text string) ParseResult {
	lowerText := strings.ToLower(text)

	var rule *rules.Rule
	var interpretation string
	var confidence float64
	var warnings []string

	key := p.extractTagKey(text)
	if key == "" {
		return ParseResult{
			Success:       false,
			OriginalText:  text,
			Interpretation: "无法识别标签键名，请在描述中明确标签名称",
			Confidence:    0,
			Suggestions:   p.getSuggestions(text),
		}
	}

	if strings.Contains(lowerText, "必须") || strings.Contains(lowerText, "must") ||
		strings.Contains(lowerText, "应该") || strings.Contains(lowerText, "should") ||
		strings.Contains(lowerText, "需要") || strings.Contains(lowerText, "need") {

		if strings.Contains(lowerText, "禁止") || strings.Contains(lowerText, "not") ||
			strings.Contains(lowerText, "不能") || strings.Contains(lowerText, "don't") {
			rule = &rules.Rule{
				ID:          fmt.Sprintf("forbidden_%s", strings.ToLower(key)),
				Name:        fmt.Sprintf("Forbidden %s Tag", key),
				Type:        rules.ForbiddenTag,
				Description: fmt.Sprintf("禁止使用 %s 标签", key),
				Key:         key,
				Severity:    "medium",
				Enabled:     true,
			}
			interpretation = fmt.Sprintf("推测规则：禁止使用 '%s' 标签", key)
			confidence = 0.6
		} else {
			values := p.extractValues(text)
			if len(values) > 0 {
				rule = &rules.Rule{
					ID:          fmt.Sprintf("values_%s", strings.ToLower(key)),
					Name:        fmt.Sprintf("%s Tag Allowed Values", key),
					Type:        rules.TagValueInList,
					Description: fmt.Sprintf("%s 标签的值必须是以下之一: %s", key, strings.Join(values, ", ")),
					Key:         key,
					Values:      values,
					Severity:    "medium",
					Enabled:     true,
				}
				interpretation = fmt.Sprintf("推测规则：'%s' 标签的值必须是 [%s] 之一", key, strings.Join(values, ", "))
				confidence = 0.7
			} else {
				rule = &rules.Rule{
					ID:          fmt.Sprintf("required_%s", strings.ToLower(key)),
					Name:        fmt.Sprintf("Required %s Tag", key),
					Type:        rules.RequiredTag,
					Description: fmt.Sprintf("所有资源必须包含 %s 标签", key),
					Key:         key,
					Severity:    "medium",
					Enabled:     true,
				}
				interpretation = fmt.Sprintf("推测规则：所有资源必须包含 '%s' 标签", key)
				confidence = 0.7
			}
		}
	} else if strings.Contains(lowerText, "禁止") || strings.Contains(lowerText, "not allowed") {
		rule = &rules.Rule{
			ID:          fmt.Sprintf("forbidden_%s", strings.ToLower(key)),
			Name:        fmt.Sprintf("Forbidden %s Tag", key),
			Type:        rules.ForbiddenTag,
			Description: fmt.Sprintf("禁止使用 %s 标签", key),
			Key:         key,
			Severity:    "medium",
			Enabled:     true,
		}
		interpretation = fmt.Sprintf("推测规则：禁止使用 '%s' 标签", key)
		confidence = 0.65
	} else {
		rule = &rules.Rule{
			ID:          fmt.Sprintf("required_%s", strings.ToLower(key)),
			Name:        fmt.Sprintf("Required %s Tag", key),
			Type:        rules.RequiredTag,
			Description: fmt.Sprintf("所有资源必须包含 %s 标签", key),
			Key:         key,
			Severity:    "medium",
			Enabled:     true,
		}
		interpretation = fmt.Sprintf("默认规则：所有资源必须包含 '%s' 标签（推测）", key)
		confidence = 0.5
		warnings = append(warnings, "规则类型不明确，已默认设为必填标签规则")
	}

	severity, hasSeverity := p.extractSeverity(text)
	if hasSeverity {
		rule.Severity = severity
		interpretation += fmt.Sprintf("，严重程度为 %s", severity)
	}

	resourceTypes := p.extractResourceTypes(text)
	if len(resourceTypes) > 0 {
		rule.ResourceTypes = resourceTypes
		typeNames := make([]string, len(resourceTypes))
		for i, rt := range resourceTypes {
			typeNames[i] = string(rt)
		}
		interpretation += fmt.Sprintf("，适用资源类型: %s", strings.Join(typeNames, ", "))
	}

	return ParseResult{
		Success:       true,
		Rule:          rule,
		OriginalText:  text,
		Interpretation: interpretation,
		Confidence:    confidence,
		Warnings:      warnings,
		Suggestions:   p.getSuggestions(text),
	}
}

func (p *NLParser) extractTagKey(text string) string {
	re := regexp.MustCompile(`["']?([A-Za-z][A-Za-z0-9_\-]+)["']?\s*(?:标签|tag)`)
	matches := re.FindStringSubmatch(text)
	if matches != nil {
		return matches[1]
	}

	words := strings.FieldsFunc(text, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r) && r != '_' && r != '-'
	})
	for _, word := range words {
		if len(word) >= 3 && unicode.IsUpper(rune(word[0])) {
			return word
		}
	}

	candidates := []string{"Environment", "Department", "CostCenter", "Owner", "Project", "Team"}
	for _, c := range candidates {
		if strings.Contains(strings.ToLower(text), strings.ToLower(c)) {
			return c
		}
	}

	return ""
}

func (p *NLParser) extractValues(text string) []string {
	re := regexp.MustCompile(`\[([^\]]+)\]`)
	matches := re.FindStringSubmatch(text)
	if matches != nil {
		return parseValueList(matches[1])
	}

	re2 := regexp.MustCompile(`["']([^"']+)["']`)
	allMatches := re2.FindAllStringSubmatch(text, -1)
	if len(allMatches) >= 2 {
		var values []string
		for _, m := range allMatches {
			values = append(values, m[1])
		}
		return values
	}

	return nil
}

func (p *NLParser) extractSeverity(text string) (string, bool) {
	lowerText := strings.ToLower(text)
	for keyword, severity := range p.severityMap {
		if strings.Contains(lowerText, keyword) {
			return severity, true
		}
	}
	return "", false
}

func (p *NLParser) extractResourceTypes(text string) []cloud.ResourceType {
	return parseResourceTypes(text)
}

func (p *NLParser) getSuggestions(text string) []string {
	return []string{
		"所有资源必须包含 Environment 标签",
		"禁止使用 Owner 标签",
		"Environment 标签的值必须是 [Production, Development, Testing] 之一",
		"CostCenter 标签的值必须匹配正则 ^CC\\d{3}$",
		"Environment 标签必须区分大小写",
		"Department 标签只能适用于 ECS 和 RDS 资源",
	}
}

func (p *NLParser) BatchParse(texts []string) []ParseResult {
	results := make([]ParseResult, len(texts))
	for i, text := range texts {
		results[i] = p.Parse(text)
	}
	return results
}

func (p *NLParser) GenerateRuleTemplates() []map[string]string {
	return []map[string]string{
		{
			"type":        "required_tag",
			"example":     "所有资源必须包含 Environment 标签",
			"description": "指定所有资源必须包含某个标签",
		},
		{
			"type":        "forbidden_tag",
			"example":     "禁止使用 Owner 标签",
			"description": "禁止使用某个已废弃的标签",
		},
		{
			"type":        "tag_value_in_list",
			"example":     "Environment 标签的值必须是 [Production, Development, Testing] 之一",
			"description": "指定标签的值只能从列表中选择",
		},
		{
			"type":        "tag_value_regex",
			"example":     "CostCenter 标签的值必须匹配正则 ^CC\\d{3}$",
			"description": "指定标签的值必须符合某个正则格式",
		},
		{
			"type":        "case_sensitive",
			"example":     "Environment 标签必须区分大小写",
			"description": "检查标签键的大小写是否正确",
		},
	}
}

func (p *NLParser) ValidateRule(rule *rules.Rule) []string {
	var errors []string

	if rule.ID == "" {
		errors = append(errors, "规则ID不能为空")
	}
	if rule.Name == "" {
		errors = append(errors, "规则名称不能为空")
	}
	if rule.Key == "" {
		errors = append(errors, "标签键不能为空")
	}
	if rule.Severity != "high" && rule.Severity != "medium" && rule.Severity != "low" {
		errors = append(errors, "严重程度必须是 high、medium 或 low")
	}
	if rule.Type == rules.TagValueInList && len(rule.Values) == 0 {
		errors = append(errors, "值列表类型的规则必须提供值列表")
	}
	if rule.Type == rules.TagValueRegex && rule.Value == "" {
		errors = append(errors, "正则类型的规则必须提供正则表达式")
	}

	return errors
}

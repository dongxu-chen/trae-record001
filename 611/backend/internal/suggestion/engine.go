package suggestion

import (
	"cloud-tag-compliance/internal/cloud"
	"cloud-tag-compliance/internal/rules"
	"regexp"
	"strings"
	"sync"
)

type TagSuggestion struct {
	Key          string   `json:"key"`
	Value        string   `json:"value"`
	Confidence   float64  `json:"confidence"`
	Reason       string   `json:"reason"`
	Source       string   `json:"source"`
	Alternatives []string `json:"alternatives,omitempty"`
}

type ResourceContext struct {
	NamePatterns     map[string][]string
	EnvironmentHints []string
	DepartmentHints  []string
	CostCenterHints  []string
}

type SuggestionEngine struct {
	context        *ResourceContext
	historicalData map[string]map[string]int
	mu             sync.RWMutex
}

func NewSuggestionEngine() *SuggestionEngine {
	engine := &SuggestionEngine{
		context:        buildDefaultContext(),
		historicalData: make(map[string]map[string]int),
	}
	return engine
}

func buildDefaultContext() *ResourceContext {
	return &ResourceContext{
		NamePatterns: map[string][]string{
			"Environment": {"prod", "production", "dev", "development", "test", "testing", "staging", "uat", "pre", "prd"},
			"Department":  {"eng", "engineering", "data", "analytics", "ops", "operations", "marketing", "sales", "finance", "hr"},
			"CostCenter":  {"cc", "cost"},
		},
		EnvironmentHints: []string{"Production", "Development", "Testing", "Staging", "UAT"},
		DepartmentHints:  []string{"Engineering", "Data", "Operations", "Marketing", "Finance"},
		CostCenterHints:  []string{"CC001", "CC002", "CC003", "CC004", "CC005"},
	}
}

func (e *SuggestionEngine) LearnFromResources(resources []cloud.Resource) {
	e.mu.Lock()
	defer e.mu.Unlock()

	for _, resource := range resources {
		for key, value := range resource.Tags {
			if _, exists := e.historicalData[key]; !exists {
				e.historicalData[key] = make(map[string]int)
			}
			e.historicalData[key][value]++
		}
	}
}

func (e *SuggestionEngine) GetSuggestions(resource cloud.Resource, ruleEngine *rules.Engine) map[string][]TagSuggestion {
	e.mu.RLock()
	defer e.mu.RUnlock()

	suggestions := make(map[string][]TagSuggestion)

	resourceName := strings.ToLower(resource.Name)
	resourceType := string(resource.Type)

	envSuggestions := e.suggestEnvironment(resourceName, resourceType, resource.Tags)
	if len(envSuggestions) > 0 {
		suggestions["Environment"] = envSuggestions
	}

	deptSuggestions := e.suggestDepartment(resourceName, resourceType, resource.Tags)
	if len(deptSuggestions) > 0 {
		suggestions["Department"] = deptSuggestions
	}

	costCenterSuggestions := e.suggestCostCenter(resourceName, resourceType, resource.Tags)
	if len(costCenterSuggestions) > 0 {
		suggestions["CostCenter"] = costCenterSuggestions
	}

	ownerSuggestions := e.suggestOwner(resourceName, resource.Tags)
	if len(ownerSuggestions) > 0 {
		suggestions["Owner"] = ownerSuggestions
	}

	projectSuggestions := e.suggestProject(resourceName, resource.Tags)
	if len(projectSuggestions) > 0 {
		suggestions["Project"] = projectSuggestions
	}

	for tagKey := range resource.Tags {
		if valueSuggestions := e.suggestTagValue(tagKey, resourceName, resource.Tags); len(valueSuggestions) > 0 {
			suggestions[tagKey] = valueSuggestions
		}
	}

	if ruleEngine != nil {
		for _, rule := range ruleEngine.GetRules() {
			if !rule.Enabled {
				continue
			}
			if _, exists := resource.Tags[rule.Key]; !exists {
				if rule.Type == rules.RequiredTag || rule.Type == rules.TagValueInList {
					if _, hasSuggestions := suggestions[rule.Key]; !hasSuggestions {
						suggestions[rule.Key] = e.suggestFromRule(rule, resourceName, resourceType)
					}
				}
			}
		}
	}

	return suggestions
}

func (e *SuggestionEngine) suggestEnvironment(resourceName, resourceType string, currentTags map[string]string) []TagSuggestion {
	if _, exists := currentTags["Environment"]; exists {
		return nil
	}

	var suggestions []TagSuggestion

	if strings.Contains(resourceName, "prod") || strings.Contains(resourceName, "prd") || strings.Contains(resourceName, "production") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Environment",
			Value:      "Production",
			Confidence: 0.9,
			Reason:     "资源名称包含 'prod'/'prd' 标识，推测为生产环境",
			Source:     "name_pattern",
		})
	}

	if strings.Contains(resourceName, "dev") || strings.Contains(resourceName, "development") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Environment",
			Value:      "Development",
			Confidence: 0.85,
			Reason:     "资源名称包含 'dev' 标识，推测为开发环境",
			Source:     "name_pattern",
		})
	}

	if strings.Contains(resourceName, "test") || strings.Contains(resourceName, "testing") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Environment",
			Value:      "Testing",
			Confidence: 0.8,
			Reason:     "资源名称包含 'test' 标识，推测为测试环境",
			Source:     "name_pattern",
		})
	}

	if strings.Contains(resourceName, "staging") || strings.Contains(resourceName, "pre") || strings.Contains(resourceName, "uat") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Environment",
			Value:      "Staging",
			Confidence: 0.8,
			Reason:     "资源名称包含 'staging'/'pre'/'uat' 标识，推测为预发布环境",
			Source:     "name_pattern",
		})
	}

	if strings.Contains(resourceName, "web") || strings.Contains(resourceName, "api") {
		suggestions = append(suggestions, TagSuggestion{
			Key:          "Environment",
			Value:        "Production",
			Confidence:   0.6,
			Reason:       "资源为Web/API服务，默认推荐生产环境",
			Source:       "resource_type",
			Alternatives: []string{"Development", "Testing"},
		})
	}

	if strings.Contains(resourceName, "db") || strings.Contains(resourceName, "mysql") || strings.Contains(resourceName, "postgres") || strings.Contains(resourceName, "redis") {
		suggestions = append(suggestions, TagSuggestion{
			Key:          "Environment",
			Value:        "Production",
			Confidence:   0.55,
			Reason:       "资源为数据库服务，根据使用场景推荐",
			Source:       "resource_type",
			Alternatives: []string{"Development", "Testing"},
		})
	}

	if histValues, exists := e.historicalData["Environment"]; exists {
		for value, count := range histValues {
			if count > 3 {
				found := false
				for _, s := range suggestions {
					if s.Value == value {
						found = true
						break
					}
				}
				if !found {
					suggestions = append(suggestions, TagSuggestion{
						Key:        "Environment",
						Value:      value,
						Confidence: 0.4,
						Reason:     "基于历史数据的常用值推荐",
						Source:     "historical",
					})
				}
			}
		}
	}

	return suggestions
}

func (e *SuggestionEngine) suggestDepartment(resourceName, resourceType string, currentTags map[string]string) []TagSuggestion {
	if _, exists := currentTags["Department"]; exists {
		return nil
	}

	var suggestions []TagSuggestion

	if strings.Contains(resourceName, "data") || strings.Contains(resourceName, "analytic") || strings.Contains(resourceName, "warehouse") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Department",
			Value:      "Data",
			Confidence: 0.85,
			Reason:     "资源名称包含 'data'/'analytic' 标识，推测属于数据部门",
			Source:     "name_pattern",
		})
	}

	if strings.Contains(resourceName, "eng") || strings.Contains(resourceName, "backend") || strings.Contains(resourceName, "frontend") || strings.Contains(resourceName, "dev") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Department",
			Value:      "Engineering",
			Confidence: 0.8,
			Reason:     "资源名称包含技术相关标识，推测属于研发部门",
			Source:     "name_pattern",
		})
	}

	if strings.Contains(resourceName, "ops") || strings.Contains(resourceName, "monitor") || strings.Contains(resourceName, "backup") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Department",
			Value:      "Operations",
			Confidence: 0.8,
			Reason:     "资源名称包含运维相关标识，推测属于运维部门",
			Source:     "name_pattern",
		})
	}

	if strings.Contains(resourceName, "market") || strings.Contains(resourceName, "campaign") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Department",
			Value:      "Marketing",
			Confidence: 0.75,
			Reason:     "资源名称包含营销相关标识，推测属于市场部门",
			Source:     "name_pattern",
		})
	}

	if strings.Contains(resourceName, "finance") || strings.Contains(resourceName, "billing") || strings.Contains(resourceName, "account") {
		suggestions = append(suggestions, TagSuggestion{
			Key:        "Department",
			Value:      "Finance",
			Confidence: 0.75,
			Reason:     "资源名称包含财务相关标识，推测属于财务部门",
			Source:     "name_pattern",
		})
	}

	if resourceType == "ECS" || resourceType == "OSS" {
		suggestions = append(suggestions, TagSuggestion{
			Key:          "Department",
			Value:        "Engineering",
			Confidence:   0.5,
			Reason:       "计算/存储资源通常由研发部门管理",
			Source:       "resource_type",
			Alternatives: []string{"Data", "Operations"},
		})
	}

	if resourceType == "RDS" {
		suggestions = append(suggestions, TagSuggestion{
			Key:          "Department",
			Value:        "Data",
			Confidence:   0.55,
			Reason:       "数据库资源通常由数据部门管理",
			Source:       "resource_type",
			Alternatives: []string{"Engineering", "Operations"},
		})
	}

	return suggestions
}

func (e *SuggestionEngine) suggestCostCenter(resourceName, resourceType string, currentTags map[string]string) []TagSuggestion {
	if _, exists := currentTags["CostCenter"]; exists {
		return nil
	}

	var suggestions []TagSuggestion

	re := regexp.MustCompile(`cc[-_]?(\d+)`)
	matches := re.FindStringSubmatch(resourceName)
	if len(matches) > 1 {
		num := matches[1]
		if len(num) < 3 {
			num = strings.Repeat("0", 3-len(num)) + num
		}
		suggestions = append(suggestions, TagSuggestion{
			Key:        "CostCenter",
			Value:      "CC" + num,
			Confidence: 0.95,
			Reason:     "从资源名称中提取到成本中心编号",
			Source:     "name_extraction",
		})
	}

	if deptSuggs := e.suggestDepartment(resourceName, resourceType, map[string]string{}); len(deptSuggs) > 0 {
		dept := deptSuggs[0].Value
		costMap := map[string]string{
			"Engineering": "CC001",
			"Data":        "CC002",
			"Operations":  "CC003",
			"Marketing":   "CC004",
			"Finance":     "CC005",
		}
		if cc, ok := costMap[dept]; ok {
			suggestions = append(suggestions, TagSuggestion{
				Key:        "CostCenter",
				Value:      cc,
				Confidence: deptSuggs[0].Confidence * 0.8,
				Reason:     "基于推测的部门映射成本中心",
				Source:     "department_inference",
			})
		}
	}

	if envSuggs := e.suggestEnvironment(resourceName, resourceType, map[string]string{}); len(envSuggs) > 0 {
		env := envSuggs[0].Value
		costMap := map[string]string{
			"Production":  "CC001",
			"Staging":     "CC002",
			"Development": "CC003",
			"Testing":     "CC003",
		}
		if cc, ok := costMap[env]; ok {
			found := false
			for _, s := range suggestions {
				if s.Value == cc {
					found = true
					break
				}
			}
			if !found {
				suggestions = append(suggestions, TagSuggestion{
					Key:        "CostCenter",
					Value:      cc,
					Confidence: envSuggs[0].Confidence * 0.6,
					Reason:     "基于推测的环境映射成本中心",
					Source:     "environment_inference",
				})
			}
		}
	}

	return suggestions
}

func (e *SuggestionEngine) suggestOwner(resourceName string, currentTags map[string]string) []TagSuggestion {
	if _, exists := currentTags["Owner"]; exists {
		return nil
	}

	var suggestions []TagSuggestion

	nameParts := strings.FieldsFunc(resourceName, func(r rune) bool {
		return r == '-' || r == '_' || r == '.'
	})

	if len(nameParts) > 0 {
		lastPart := nameParts[len(nameParts)-1]
		if len(lastPart) >= 2 && len(lastPart) <= 8 && !containsNumber(lastPart) {
			suggestions = append(suggestions, TagSuggestion{
				Key:        "Owner",
				Value:      lastPart,
				Confidence: 0.5,
				Reason:     "从资源名称后缀推测负责人",
				Source:     "name_pattern",
			})
		}
	}

	return suggestions
}

func (e *SuggestionEngine) suggestProject(resourceName string, currentTags map[string]string) []TagSuggestion {
	if _, exists := currentTags["Project"]; exists {
		return nil
	}

	var suggestions []TagSuggestion

	projectKeywords := []string{"user", "order", "payment", "product", "inventory", "search", "recommend", "ai", "ml", "analytics", "report", "dashboard"}
	lowerName := strings.ToLower(resourceName)

	for _, kw := range projectKeywords {
		if strings.Contains(lowerName, kw) {
			suggestions = append(suggestions, TagSuggestion{
				Key:        "Project",
				Value:      strings.Title(kw),
				Confidence: 0.65,
				Reason:     "资源名称包含项目关键词 '" + kw + "'",
				Source:     "name_pattern",
			})
		}
	}

	return suggestions
}

func (e *SuggestionEngine) suggestTagValue(tagKey, resourceName string, currentTags map[string]string) []TagSuggestion {
	currentValue, exists := currentTags[tagKey]
	if !exists {
		return nil
	}

	var suggestions []TagSuggestion

	if histValues, ok := e.historicalData[tagKey]; ok {
		total := 0
		for _, count := range histValues {
			total += count
		}

		normalizedCurrent := strings.ToLower(currentValue)
		for value, count := range histValues {
			if strings.ToLower(value) == normalizedCurrent {
				continue
			}
			if count > total/10 {
				suggestions = append(suggestions, TagSuggestion{
					Key:        tagKey,
					Value:      value,
					Confidence: float64(count) / float64(total),
					Reason:     "历史数据中常用值",
					Source:     "historical",
				})
			}
		}
	}

	return suggestions
}

func (e *SuggestionEngine) suggestFromRule(rule rules.Rule, resourceName, resourceType string) []TagSuggestion {
	var suggestions []TagSuggestion

	switch rule.Type {
	case rules.RequiredTag:
		if len(rule.Values) > 0 {
			for i, value := range rule.Values {
				confidence := 0.5 - float64(i)*0.1
				if confidence < 0.2 {
					confidence = 0.2
				}
				suggestions = append(suggestions, TagSuggestion{
					Key:        rule.Key,
					Value:      value,
					Confidence: confidence,
					Reason:     "规则定义的推荐值",
					Source:     "rule_based",
				})
			}
		} else {
			suggestions = append(suggestions, TagSuggestion{
				Key:        rule.Key,
				Value:      "请填写",
				Confidence: 0.1,
				Reason:     "规则要求必填，请根据实际情况填写",
				Source:     "rule_based",
			})
		}

	case rules.TagValueInList:
		for i, value := range rule.Values {
			confidence := 0.6 - float64(i)*0.1
			if confidence < 0.3 {
				confidence = 0.3
			}
			suggestions = append(suggestions, TagSuggestion{
				Key:        rule.Key,
				Value:      value,
				Confidence: confidence,
				Reason:     "规则允许的值",
				Source:     "rule_based",
			})
		}
	}

	return suggestions
}

func containsNumber(s string) bool {
	for _, r := range s {
		if r >= '0' && r <= '9' {
			return true
		}
	}
	return false
}

func (e *SuggestionEngine) GetSmartSuggestions(resource cloud.Resource, ruleEngine *rules.Engine) map[string]interface{} {
	suggestions := e.GetSuggestions(resource, ruleEngine)

	result := make(map[string]interface{})
	result["resourceId"] = resource.ID
	result["resourceName"] = resource.Name
	result["currentTags"] = resource.Tags
	result["suggestions"] = suggestions

	summary := make(map[string]interface{})
	totalSuggestions := 0
	highConfidence := 0
	for key, suggs := range suggestions {
		totalSuggestions += len(suggs)
		for _, s := range suggs {
			if s.Confidence >= 0.8 {
				highConfidence++
			}
		}
		_ = key
	}
	summary["totalSuggestions"] = totalSuggestions
	summary["highConfidenceCount"] = highConfidence
	summary["missingRequiredTags"] = e.getMissingRequiredTags(resource, ruleEngine)
	result["summary"] = summary

	return result
}

func (e *SuggestionEngine) getMissingRequiredTags(resource cloud.Resource, ruleEngine *rules.Engine) []string {
	var missing []string
	if ruleEngine == nil {
		return missing
	}

	for _, rule := range ruleEngine.GetRules() {
		if !rule.Enabled {
			continue
		}
		if rule.Type == rules.RequiredTag {
			if _, exists := resource.Tags[rule.Key]; !exists {
				missing = append(missing, rule.Key)
			}
		}
	}
	return missing
}

func (e *SuggestionEngine) BatchSuggest(resources []cloud.Resource, ruleEngine *rules.Engine) map[string]interface{} {
	results := make(map[string]interface{})
	allSuggestions := make(map[string]map[string][]TagSuggestion)

	for _, resource := range resources {
		suggs := e.GetSuggestions(resource, ruleEngine)
		allSuggestions[resource.ID] = suggs
	}

	stats := make(map[string]interface{})
	totalResources := len(resources)
	resourcesWithSuggestions := 0
	totalSuggestions := 0
	highConfidenceCount := 0

	for _, suggs := range allSuggestions {
		if len(suggs) > 0 {
			resourcesWithSuggestions++
		}
		for _, tagSuggs := range suggs {
			totalSuggestions += len(tagSuggs)
			for _, s := range tagSuggs {
				if s.Confidence >= 0.8 {
					highConfidenceCount++
				}
			}
		}
	}

	stats["totalResources"] = totalResources
	stats["resourcesWithSuggestions"] = resourcesWithSuggestions
	stats["totalSuggestions"] = totalSuggestions
	stats["highConfidenceCount"] = highConfidenceCount

	results["stats"] = stats
	results["suggestions"] = allSuggestions

	return results
}

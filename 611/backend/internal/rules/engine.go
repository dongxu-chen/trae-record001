package rules

import (
	"cloud-tag-compliance/internal/cloud"
	"os"
	"regexp"
	"strings"

	"gopkg.in/yaml.v3"
)

type RuleType string

const (
	RequiredTag    RuleType = "required_tag"
	ForbiddenTag   RuleType = "forbidden_tag"
	TagValueRegex  RuleType = "tag_value_regex"
	TagValueInList RuleType = "tag_value_in_list"
	CaseSensitive  RuleType = "case_sensitive"
)

type Rule struct {
	ID          string        `yaml:"id" json:"id"`
	Name        string        `yaml:"name" json:"name"`
	Type        RuleType      `yaml:"type" json:"type"`
	Description string        `yaml:"description" json:"description"`
	Key         string        `yaml:"key" json:"key"`
	Value       string        `yaml:"value" json:"value"`
	Values      []string      `yaml:"values" json:"values"`
	ResourceTypes []cloud.ResourceType `yaml:"resourceTypes" json:"resourceTypes"`
	Severity    string        `yaml:"severity" json:"severity"`
	Enabled     bool          `yaml:"enabled" json:"enabled"`
}

type Violation struct {
	ResourceID   string              `json:"resourceId"`
	ResourceName string              `json:"resourceName"`
	ResourceType cloud.ResourceType  `json:"resourceType"`
	AccountID    string              `json:"accountId"`
	AccountName  string              `json:"accountName"`
	RuleID       string              `json:"ruleId"`
	RuleName     string              `json:"ruleName"`
	Severity     string              `json:"severity"`
	Message      string              `json:"message"`
	TagKey       string              `json:"tagKey"`
	Expected     string              `json:"expected,omitempty"`
	Actual       string              `json:"actual,omitempty"`
}

type ComplianceResult struct {
	TotalResources int         `json:"totalResources"`
	Compliant      int         `json:"compliant"`
	NonCompliant   int         `json:"nonCompliant"`
	Violations     []Violation `json:"violations"`
	ComplianceRate float64     `json:"complianceRate"`
}

type Engine struct {
	rules []Rule
}

func NewEngine() *Engine {
	return &Engine{
		rules: []Rule{},
	}
}

func (e *Engine) LoadRules(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	var rules struct {
		Rules []Rule `yaml:"rules"`
	}
	if err := yaml.Unmarshal(data, &rules); err != nil {
		return err
	}

	e.rules = rules.Rules
	return nil
}

func (e *Engine) GetRules() []Rule {
	return e.rules
}

func (e *Engine) AddRule(rule Rule) {
	e.rules = append(e.rules, rule)
}

func (e *Engine) CheckResource(resource cloud.Resource) []Violation {
	var violations []Violation

	for _, rule := range e.rules {
		if !rule.Enabled {
			continue
		}

		if len(rule.ResourceTypes) > 0 {
			matches := false
			for _, rt := range rule.ResourceTypes {
				if rt == resource.Type {
					matches = true
					break
				}
			}
			if !matches {
				continue
			}
		}

		if violation := e.applyRule(rule, resource); violation != nil {
			violations = append(violations, *violation)
		}
	}

	return violations
}

func (e *Engine) applyRule(rule Rule, resource cloud.Resource) *Violation {
	switch rule.Type {
	case RequiredTag:
		if _, exists := resource.Tags[rule.Key]; !exists {
			return &Violation{
				ResourceID:   resource.ID,
				ResourceName: resource.Name,
				ResourceType: resource.Type,
				AccountID:    resource.AccountID,
				AccountName:  resource.AccountName,
				RuleID:       rule.ID,
				RuleName:     rule.Name,
				Severity:     rule.Severity,
				Message:      "Missing required tag",
				TagKey:       rule.Key,
				Expected:     rule.Key + " tag must exist",
			}
		}

	case ForbiddenTag:
		if _, exists := resource.Tags[rule.Key]; exists {
			return &Violation{
				ResourceID:   resource.ID,
				ResourceName: resource.Name,
				ResourceType: resource.Type,
				AccountID:    resource.AccountID,
				AccountName:  resource.AccountName,
				RuleID:       rule.ID,
				RuleName:     rule.Name,
				Severity:     rule.Severity,
				Message:      "Forbidden tag found",
				TagKey:       rule.Key,
				Expected:     rule.Key + " tag should not exist",
				Actual:       resource.Tags[rule.Key],
			}
		}

	case TagValueRegex:
		value, exists := resource.Tags[rule.Key]
		if !exists {
			return nil
		}
		matched, _ := regexp.MatchString(rule.Value, value)
		if !matched {
			return &Violation{
				ResourceID:   resource.ID,
				ResourceName: resource.Name,
				ResourceType: resource.Type,
				AccountID:    resource.AccountID,
				AccountName:  resource.AccountName,
				RuleID:       rule.ID,
				RuleName:     rule.Name,
				Severity:     rule.Severity,
				Message:      "Tag value does not match pattern",
				TagKey:       rule.Key,
				Expected:     "match pattern: " + rule.Value,
				Actual:       value,
			}
		}

	case TagValueInList:
		value, exists := resource.Tags[rule.Key]
		if !exists {
			return nil
		}
		found := false
		for _, v := range rule.Values {
			if v == value {
				found = true
				break
			}
		}
		if !found {
			return &Violation{
				ResourceID:   resource.ID,
				ResourceName: resource.Name,
				ResourceType: resource.Type,
				AccountID:    resource.AccountID,
				AccountName:  resource.AccountName,
				RuleID:       rule.ID,
				RuleName:     rule.Name,
				Severity:     rule.Severity,
				Message:      "Tag value not in allowed list",
				TagKey:       rule.Key,
				Expected:     "one of: " + strings.Join(rule.Values, ", "),
				Actual:       value,
			}
		}

	case CaseSensitive:
		for key := range resource.Tags {
			if strings.ToLower(key) == strings.ToLower(rule.Key) && key != rule.Key {
				return &Violation{
					ResourceID:   resource.ID,
					ResourceName: resource.Name,
					ResourceType: resource.Type,
					AccountID:    resource.AccountID,
					AccountName:  resource.AccountName,
					RuleID:       rule.ID,
					RuleName:     rule.Name,
					Severity:     rule.Severity,
					Message:      "Tag key case sensitivity issue",
					TagKey:       key,
					Expected:     rule.Key,
					Actual:       key,
				}
			}
		}
	}

	return nil
}

func (e *Engine) CheckResources(resources []cloud.Resource) ComplianceResult {
	var allViolations []Violation
	nonCompliantSet := make(map[string]bool)

	for _, resource := range resources {
		violations := e.CheckResource(resource)
		if len(violations) > 0 {
			nonCompliantSet[resource.ID] = true
			allViolations = append(allViolations, violations...)
		}
	}

	nonCompliantCount := len(nonCompliantSet)
	compliantCount := len(resources) - nonCompliantCount
	complianceRate := 0.0
	if len(resources) > 0 {
		complianceRate = float64(compliantCount) / float64(len(resources)) * 100
	}

	return ComplianceResult{
		TotalResources: len(resources),
		Compliant:      compliantCount,
		NonCompliant:   nonCompliantCount,
		Violations:     allViolations,
		ComplianceRate: complianceRate,
	}
}

func (e *Engine) GetTagSuggestions(resource cloud.Resource) map[string][]string {
	suggestions := make(map[string][]string)

	for _, rule := range e.rules {
		if !rule.Enabled {
			continue
		}

		switch rule.Type {
		case RequiredTag:
			if _, exists := resource.Tags[rule.Key]; !exists {
				suggestions[rule.Key] = []string{"Add required tag"}
				if len(rule.Values) > 0 {
					suggestions[rule.Key] = append(suggestions[rule.Key], rule.Values...)
				}
			}
		case TagValueInList:
			if _, exists := resource.Tags[rule.Key]; exists {
				suggestions[rule.Key] = rule.Values
			} else {
				suggestions[rule.Key] = append([]string{"Add tag with value from list"}, rule.Values...)
			}
		}
	}

	return suggestions
}

func (e *Engine) ValidateRule(rule Rule) (bool, string) {
	if rule.Name == "" {
		return false, "规则名称不能为空"
	}
	if rule.Key == "" {
		return false, "标签键不能为空"
	}

	switch rule.Type {
	case RequiredTag, ForbiddenTag, CaseSensitive:
		return true, ""
	case TagValueRegex:
		if rule.Value == "" {
			return false, "正则表达式不能为空"
		}
		if _, err := regexp.Compile(rule.Value); err != nil {
			return false, "正则表达式无效: " + err.Error()
		}
		return true, ""
	case TagValueInList:
		if len(rule.Values) == 0 {
			return false, "标签值列表不能为空"
		}
		return true, ""
	default:
		return false, "未知的规则类型: " + string(rule.Type)
	}
}

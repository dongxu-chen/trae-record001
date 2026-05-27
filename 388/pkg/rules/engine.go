package rules

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"gopkg.in/yaml.v3"
)

type Rule struct {
	Name        string            `yaml:"name"`
	Description string            `yaml:"description"`
	Severity    string            `yaml:"severity"`
	EventType   string            `yaml:"event_type"`
	Condition   string            `yaml:"condition"`
	Output      string            `yaml:"output"`
	Remediation string            `yaml:"remediation"`
	Tags        []string          `yaml:"tags"`
	Enabled     bool              `yaml:"enabled"`
	compiled    *regexp.Regexp
}

type Engine struct {
	rules map[string][]*Rule
}

func NewEngine(rulesDir string) (*Engine, error) {
	engine := &Engine{
		rules: make(map[string][]*Rule),
	}

	if err := engine.loadRules(rulesDir); err != nil {
		return nil, err
	}

	return engine, nil
}

func (e *Engine) loadRules(rulesDir string) error {
	err := filepath.Walk(rulesDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() || (!strings.HasSuffix(path, ".yaml") && !strings.HasSuffix(path, ".yml")) {
			return nil
		}

		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}

		var rules []*Rule
		if err := yaml.Unmarshal(data, &rules); err != nil {
			return fmt.Errorf("failed to parse %s: %v", path, err)
		}

		for _, rule := range rules {
			if !rule.Enabled {
				continue
			}

			compiled, err := regexp.Compile(rule.Condition)
			if err != nil {
				return fmt.Errorf("invalid regex in rule %s: %v", rule.Name, err)
			}
			rule.compiled = compiled

			e.rules[rule.EventType] = append(e.rules[rule.EventType], rule)
		}

		return nil
	})

	if os.IsNotExist(err) {
		return nil
	}

	return err
}

func (e *Engine) Match(eventType string, eventData map[string]interface{}) []*Rule {
	var matchedRules []*Rule

	rules, ok := e.rules[eventType]
	if !ok {
		return matchedRules
	}

	eventStr := fmt.Sprintf("%v", eventData)

	for _, rule := range rules {
		if rule.compiled.MatchString(eventStr) {
			matchedRules = append(matchedRules, rule)
		}
	}

	return matchedRules
}

func (e *Engine) GetAllRules() map[string][]*Rule {
	return e.rules
}

func (e *Engine) AddRule(rule *Rule) error {
	compiled, err := regexp.Compile(rule.Condition)
	if err != nil {
		return err
	}
	rule.compiled = compiled
	e.rules[rule.EventType] = append(e.rules[rule.EventType], rule)
	return nil
}

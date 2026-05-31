package templates

import (
	"cloud-tag-compliance/internal/cloud"
	"encoding/json"
	"os"
	"strings"
	"sync"
)

type TagTemplate struct {
	ID          string            `json:"id" yaml:"id"`
	Name        string            `json:"name" yaml:"name"`
	Description string            `json:"description" yaml:"description"`
	Tags        map[string]string `json:"tags" yaml:"tags"`
	AutoApply   bool              `json:"autoApply" yaml:"autoApply"`
	Priority    int               `json:"priority" yaml:"priority"`
	Conditions  TemplateCondition `json:"conditions" yaml:"conditions"`
	CreatedAt   string            `json:"createdAt" yaml:"createdAt"`
	UpdatedAt   string            `json:"updatedAt" yaml:"updatedAt"`
	Enabled     bool              `json:"enabled" yaml:"enabled"`
}

type TemplateCondition struct {
	ResourceTypes []string `json:"resourceTypes" yaml:"resourceTypes"`
	AccountIDs    []string `json:"accountIds" yaml:"accountIds"`
	NamePattern   string   `json:"namePattern" yaml:"namePattern"`
	Regions       []string `json:"regions" yaml:"regions"`
}

type TemplateManager struct {
	mu           sync.RWMutex
	templates    map[string]TagTemplate
	templateFile string
}

func NewTemplateManager(templateFile string) *TemplateManager {
	manager := &TemplateManager{
		templates:    make(map[string]TagTemplate),
		templateFile: templateFile,
	}
	manager.load()
	manager.initDefaultTemplates()
	return manager
}

func (m *TemplateManager) load() {
	if m.templateFile == "" {
		return
	}

	data, err := os.ReadFile(m.templateFile)
	if err != nil {
		return
	}

	var templates []TagTemplate
	if err := json.Unmarshal(data, &templates); err == nil {
		for _, t := range templates {
			m.templates[t.ID] = t
		}
	}
}

func (m *TemplateManager) save() {
	if m.templateFile == "" {
		return
	}

	m.mu.RLock()
	defer m.mu.RUnlock()

	templates := make([]TagTemplate, 0, len(m.templates))
	for _, t := range m.templates {
		templates = append(templates, t)
	}

	data, err := json.MarshalIndent(templates, "", "  ")
	if err != nil {
		return
	}

	os.WriteFile(m.templateFile, data, 0644)
}

func (m *TemplateManager) initDefaultTemplates() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if len(m.templates) > 0 {
		return
	}

	defaultTemplates := []TagTemplate{
		{
			ID:          "template-env-prod",
			Name:        "生产环境资源",
			Description: "生产环境所有资源自动打标",
			Tags: map[string]string{
				"Environment": "Production",
				"CostCenter":  "CC100",
			},
			AutoApply: true,
			Priority:  100,
			Conditions: TemplateCondition{
				NamePattern: "prod",
			},
			Enabled: true,
		},
		{
			ID:          "template-env-dev",
			Name:        "开发环境资源",
			Description: "开发环境所有资源自动打标",
			Tags: map[string]string{
				"Environment": "Development",
				"CostCenter":  "CC200",
			},
			AutoApply: true,
			Priority:  90,
			Conditions: TemplateCondition{
				NamePattern: "dev",
			},
			Enabled: true,
		},
		{
			ID:          "template-ecs-standard",
			Name:        "ECS标准标签",
			Description: "ECS服务器标准标签集",
			Tags: map[string]string{
				"Department": "Engineering",
				"Owner":      "devops@example.com",
			},
			AutoApply: true,
			Priority:  80,
			Conditions: TemplateCondition{
				ResourceTypes: []string{"ECS"},
			},
			Enabled: true,
		},
		{
			ID:          "template-rds-database",
			Name:        "数据库标准标签",
			Description: "RDS数据库标准标签集",
			Tags: map[string]string{
				"Department": "Data",
				"Backup":     "Enabled",
			},
			AutoApply: true,
			Priority:  80,
			Conditions: TemplateCondition{
				ResourceTypes: []string{"RDS"},
			},
			Enabled: true,
		},
		{
			ID:          "template-oss-storage",
			Name:        "存储标准标签",
			Description: "OSS存储标准标签集",
			Tags: map[string]string{
				"Department": "Engineering",
				"Retention":  "30days",
			},
			AutoApply: true,
			Priority:  80,
			Conditions: TemplateCondition{
				ResourceTypes: []string{"OSS"},
			},
			Enabled: true,
		},
		{
			ID:          "template-finance-resources",
			Name:        "财务系统资源",
			Description: "财务相关资源自动打标",
			Tags: map[string]string{
				"Department": "Finance",
				"Compliance": "Strict",
			},
			AutoApply: true,
			Priority:  95,
			Conditions: TemplateCondition{
				NamePattern: "finance|fin-|pay",
			},
			Enabled: true,
		},
	}

	for _, t := range defaultTemplates {
		m.templates[t.ID] = t
	}

	go m.save()
}

func (m *TemplateManager) Create(template TagTemplate) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	template.ID = "template-" + generateID()
	m.templates[template.ID] = template

	go m.save()
	return nil
}

func (m *TemplateManager) Update(template TagTemplate) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.templates[template.ID] = template

	go m.save()
	return nil
}

func (m *TemplateManager) Delete(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	delete(m.templates, id)

	go m.save()
	return nil
}

func (m *TemplateManager) Get(id string) (TagTemplate, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	t, ok := m.templates[id]
	return t, ok
}

func (m *TemplateManager) GetAll() []TagTemplate {
	m.mu.RLock()
	defer m.mu.RUnlock()

	templates := make([]TagTemplate, 0, len(m.templates))
	for _, t := range m.templates {
		templates = append(templates, t)
	}

	return templates
}

func (m *TemplateManager) GetAutoApplyTemplates() []TagTemplate {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var templates []TagTemplate
	for _, t := range m.templates {
		if t.AutoApply && t.Enabled {
			templates = append(templates, t)
		}
	}

	return templates
}

func (m *TemplateManager) MatchTemplates(resource cloud.Resource) []TagTemplate {
	allTemplates := m.GetAutoApplyTemplates()

	var matched []TagTemplate
	for _, t := range allTemplates {
		if m.matchCondition(t, resource) {
			matched = append(matched, t)
		}
	}

	return matched
}

func (m *TemplateManager) matchCondition(template TagTemplate, resource cloud.Resource) bool {
	cond := template.Conditions

	if len(cond.ResourceTypes) > 0 {
		matched := false
		for _, rt := range cond.ResourceTypes {
			if strings.ToLower(rt) == strings.ToLower(string(resource.Type)) {
				matched = true
				break
			}
		}
		if !matched {
			return false
		}
	}

	if len(cond.AccountIDs) > 0 {
		matched := false
		for _, aid := range cond.AccountIDs {
			if aid == resource.AccountID {
				matched = true
				break
			}
		}
		if !matched {
			return false
		}
	}

	if cond.NamePattern != "" {
		patterns := strings.Split(cond.NamePattern, "|")
		matched := false
		for _, p := range patterns {
			if strings.Contains(strings.ToLower(resource.Name), strings.ToLower(strings.TrimSpace(p))) {
				matched = true
				break
			}
		}
		if !matched {
			return false
		}
	}

	if len(cond.Regions) > 0 {
		matched := false
		for _, r := range cond.Regions {
			if strings.Contains(resource.Region, r) {
				matched = true
				break
			}
		}
		if !matched {
			return false
		}
	}

	return true
}

func (m *TemplateManager) ApplyTemplates(resource cloud.Resource) map[string]string {
	matched := m.MatchTemplates(resource)

	result := make(map[string]string)
	for k, v := range resource.Tags {
		result[k] = v
	}

	for k, v := range m.ApplyTemplateTags(matched) {
		if _, exists := result[k]; !exists {
			result[k] = v
		}
	}

	return result
}

func (m *TemplateManager) ApplyTemplateTags(templates []TagTemplate) map[string]string {
	tags := make(map[string]string)

	for _, t := range templates {
		for k, v := range t.Tags {
			tags[k] = v
		}
	}

	return tags
}

func (m *TemplateManager) ApplyTemplateToResource(resourceID string, templateID string) (map[string]string, bool) {
	template, ok := m.Get(templateID)
	if !ok {
		return nil, false
	}

	return template.Tags, true
}

func generateID() string {
	return "tpl-" + randomString(8)
}

func randomString(n int) string {
	const charset = "abcdefghijklmnopqrstuvwxyz0123456789"
	b := make([]byte, n)
	for i := range b {
		b[i] = charset[(i*31)%len(charset)]
	}
	return string(b)
}

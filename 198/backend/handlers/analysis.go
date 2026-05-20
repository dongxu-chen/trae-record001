package handlers

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"prometheus-alert-manager/backend/models"
	"prometheus-alert-manager/backend/services"
)

type AnalysisHandler struct {
	db *gorm.DB
}

func NewAnalysisHandler(db *gorm.DB) *AnalysisHandler {
	return &AnalysisHandler{db: db}
}

func (h *AnalysisHandler) AnalyzeRule(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid rule ID"})
		return
	}

	var rule models.AlertRule
	if err := h.db.First(&rule, uint(id)).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}

	analysis, err := services.AnalyzeRulePerformance(rule.Expr, rule.Name, c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"rule_id":  id,
		"rule_name": rule.Name,
		"analysis": analysis,
	})
}

func (h *AnalysisHandler) AnalyzeAllRules(c *gin.Context) {
	var rules []models.AlertRule
	if err := h.db.Find(&rules).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	analyses := []map[string]interface{}{}
	totalComplexity := 0
	highLoadCount := 0
	totalCardinality := int64(0)

	for _, rule := range rules {
		analysis, err := services.AnalyzeRulePerformance(rule.Expr, rule.Name, strconv.FormatUint(uint64(rule.ID), 10))
		if err != nil {
			continue
		}

		analyses = append(analyses, map[string]interface{}{
			"rule_id":          rule.ID,
			"rule_name":        rule.Name,
			"complexity":       analysis.Complexity,
			"complexity_score": analysis.ComplexityScore,
			"estimated_load":   analysis.EstimatedLoad,
			"query_type":       analysis.QueryType,
			"total_cardinality": analysis.TotalCardinality,
			"metrics_count":    len(analysis.MetricsUsed),
		})

		totalComplexity += analysis.ComplexityScore
		totalCardinality += analysis.TotalCardinality
		if analysis.Complexity == "high" || analysis.Complexity == "critical" {
			highLoadCount++
		}
	}

	avgComplexity := 0
	if len(analyses) > 0 {
		avgComplexity = totalComplexity / len(analyses)
	}

	c.JSON(http.StatusOK, gin.H{
		"analyses":        analyses,
		"total_rules":     len(analyses),
		"high_load_count": highLoadCount,
		"avg_complexity":  avgComplexity,
		"total_cardinality": totalCardinality,
	})
}

func (h *AnalysisHandler) AnalyzeDependencies(c *gin.Context) {
	var rules []models.AlertRule
	if err := h.db.Find(&rules).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	ruleInputs := []struct {
		ID   string
		Name string
		Expr string
	}{}

	for _, rule := range rules {
		ruleInputs = append(ruleInputs, struct {
			ID   string
			Name string
			Expr string
		}{
			ID:   strconv.FormatUint(uint64(rule.ID), 10),
			Name: rule.Name,
			Expr: rule.Expr,
		})
	}

	analysis, err := services.AnalyzeRuleDependencies(ruleInputs)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ruleNameMap := make(map[string]string)
	for _, rule := range rules {
		ruleNameMap[strconv.FormatUint(uint64(rule.ID), 10)] = rule.Name
	}

	namedChains := [][]map[string]interface{}{}
	for _, chain := range analysis.Chains {
		namedChain := []map[string]interface{}{}
		for _, id := range chain {
			namedChain = append(namedChain, map[string]interface{}{
				"id":   id,
				"name": ruleNameMap[id],
			})
		}
		namedChains = append(namedChains, namedChain)
	}

	namedCriticalChains := [][]map[string]interface{}{}
	for _, chain := range analysis.CriticalChains {
		namedChain := []map[string]interface{}{}
		for _, id := range chain {
			namedChain = append(namedChain, map[string]interface{}{
				"id":   id,
				"name": ruleNameMap[id],
			})
		}
		namedCriticalChains = append(namedCriticalChains, namedChain)
	}

	c.JSON(http.StatusOK, gin.H{
		"rules":            analysis.Rules,
		"chains":           namedChains,
		"critical_chains":  namedCriticalChains,
		"independent_rules": analysis.Independent,
		"hot_metrics":      analysis.HotMetrics,
		"summary": map[string]interface{}{
			"total_rules":         len(analysis.Rules),
			"total_chains":        len(analysis.Chains),
			"critical_chains":     len(analysis.CriticalChains),
			"independent_rules":   len(analysis.Independent),
			"hot_metrics":         len(analysis.HotMetrics),
		},
	})
}

func (h *AnalysisHandler) GetRuleChain(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid rule ID"})
		return
	}

	var rules []models.AlertRule
	if err := h.db.Find(&rules).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	ruleInputs := []struct {
		ID   string
		Name string
		Expr string
	}{}
	for _, rule := range rules {
		ruleInputs = append(ruleInputs, struct {
			ID   string
			Name string
			Expr string
		}{
			ID:   strconv.FormatUint(uint64(rule.ID), 10),
			Name: rule.Name,
			Expr: rule.Expr,
		})
	}

	analysis, err := services.AnalyzeRuleDependencies(ruleInputs)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ruleIDStr := strconv.FormatUint(id, 10)
	var targetRule *services.RuleDependency
	for i := range analysis.Rules {
		if analysis.Rules[i].RuleID == ruleIDStr {
			targetRule = &analysis.Rules[i]
			break
		}
	}

	if targetRule == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found in analysis"})
		return
	}

	relatedChains := [][]string{}
	for _, chain := range analysis.Chains {
		for _, rid := range chain {
			if rid == ruleIDStr {
				relatedChains = append(relatedChains, chain)
				break
			}
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"rule": targetRule,
		"related_chains": relatedChains,
		"downstream_impact": len(targetRule.DependedBy),
		"upstream_dependencies": len(targetRule.DependsOn),
	})
}

func (h *AnalysisHandler) GetTemplates(c *gin.Context) {
	templates := services.GetBuiltinTemplates()

	withCounts := []map[string]interface{}{}
	for _, cat := range templates {
		withCounts = append(withCounts, map[string]interface{}{
			"id":          cat.ID,
			"name":        cat.Name,
			"description": cat.Description,
			"icon":        cat.Icon,
			"count":       len(cat.Templates),
			"templates":   cat.Templates,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"categories": withCounts,
		"total_categories": len(withCounts),
		"total_templates": func() int {
			total := 0
			for _, cat := range templates {
				total += len(cat.Templates)
			}
			return total
		}(),
	})
}

func (h *AnalysisHandler) GetTemplateByID(c *gin.Context) {
	templateID := c.Param("templateId")
	categories := services.GetBuiltinTemplates()

	for _, cat := range categories {
		for _, tpl := range cat.Templates {
			if tpl.ID == templateID {
				c.JSON(http.StatusOK, gin.H{
					"template": tpl,
					"category": cat.Name,
				})
				return
			}
		}
	}

	c.JSON(http.StatusNotFound, gin.H{"error": "Template not found"})
}

func (h *AnalysisHandler) ApplyTemplate(c *gin.Context) {
	templateID := c.Param("templateId")
	var req struct {
		GroupID *uint  `json:"group_id"`
		Prefix  string `json:"prefix"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	categories := services.GetBuiltinTemplates()
	var template *services.RuleTemplate

	for _, cat := range categories {
		for _, tpl := range cat.Templates {
			if tpl.ID == templateID {
				template = &tpl
				break
			}
		}
	}

	if template == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Template not found"})
		return
	}

	ruleName := template.Name
	if req.Prefix != "" {
		ruleName = req.Prefix + " - " + ruleName
	}

	newRule := models.AlertRule{
		Name:        ruleName,
		Expr:        template.Expr,
		For:         template.For,
		Severity:    template.Severity,
		Summary:     template.Summary,
		Description: template.DescriptionTemplate,
		Labels:      models.LabelsMap(template.Labels),
		Annotations: models.LabelsMap(template.Annotations),
	}

	if req.GroupID != nil {
		newRule.GroupID = *req.GroupID
	}

	if err := h.db.Create(&newRule).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	version := models.AlertRuleVersion{
		RuleID:      newRule.ID,
		Version:     1,
		Name:        newRule.Name,
		Expr:        newRule.Expr,
		For:         newRule.For,
		Severity:    newRule.Severity,
		Summary:     newRule.Summary,
		Description: newRule.Description,
		Labels:      newRule.Labels,
		Annotations: newRule.Annotations,
		ChangeLog:   "Created from template: " + template.Name,
	}

	if err := h.db.Create(&version).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":  "Successfully created rule from template",
		"rule_id":  newRule.ID,
		"rule":     newRule,
		"template": template.Name,
	})
}

func (h *AnalysisHandler) BatchApplyCategory(c *gin.Context) {
	categoryID := c.Param("categoryId")
	var req struct {
		GroupID *uint  `json:"group_id"`
		Prefix  string `json:"prefix"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	categories := services.GetBuiltinTemplates()
	var category *services.TemplateCategory

	for _, cat := range categories {
		if cat.ID == categoryID {
			category = &cat
			break
		}
	}

	if category == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Category not found"})
		return
	}

	createdRules := []models.AlertRule{}
	for _, tpl := range category.Templates {
		ruleName := tpl.Name
		if req.Prefix != "" {
			ruleName = req.Prefix + " - " + ruleName
		}

		rule := models.AlertRule{
			Name:        ruleName,
			Expr:        tpl.Expr,
			For:         tpl.For,
			Severity:    tpl.Severity,
			Summary:     tpl.Summary,
			Description: tpl.DescriptionTemplate,
			Labels:      models.LabelsMap(tpl.Labels),
			Annotations: models.LabelsMap(tpl.Annotations),
		}

		if req.GroupID != nil {
			rule.GroupID = *req.GroupID
		}

		if err := h.db.Create(&rule).Error; err != nil {
			continue
		}

		version := models.AlertRuleVersion{
			RuleID:      rule.ID,
			Version:     1,
			Name:        rule.Name,
			Expr:        rule.Expr,
			For:         rule.For,
			Severity:    rule.Severity,
			Summary:     rule.Summary,
			Description: rule.Description,
			Labels:      rule.Labels,
			Annotations: rule.Annotations,
			ChangeLog:   "Created from template: " + tpl.Name + " (category: " + category.Name + ")",
		}
		h.db.Create(&version)

		createdRules = append(createdRules, rule)
	}

	c.JSON(http.StatusOK, gin.H{
		"message":       "Successfully created rules from category",
		"created_count": len(createdRules),
		"category":      category.Name,
		"rules":         createdRules,
	})
}

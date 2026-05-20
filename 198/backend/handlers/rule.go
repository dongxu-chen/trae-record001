package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"reflect"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"gopkg.in/yaml.v3"

	"prometheus-alert-manager/models"
	"prometheus-alert-manager/services"
)

type RuleHandler struct {
	db *gorm.DB
}

func NewRuleHandler(db *gorm.DB) *RuleHandler {
	return &RuleHandler{db: db}
}

type CreateRuleRequest struct {
	GroupID     string `json:"group_id" binding:"required"`
	Name        string `json:"name" binding:"required"`
	Expr        string `json:"expr" binding:"required"`
	For         string `json:"for"`
	Severity    string `json:"severity"`
	Description string `json:"description"`
	Summary     string `json:"summary"`
	Labels      string `json:"labels"`
	Annotations string `json:"annotations"`
	Enabled     bool   `json:"enabled"`
	ChangeLog   string `json:"change_log"`
}

type UpdateRuleRequest struct {
	GroupID     string `json:"group_id"`
	Name        string `json:"name"`
	Expr        string `json:"expr"`
	For         string `json:"for"`
	Severity    string `json:"severity"`
	Description string `json:"description"`
	Summary     string `json:"summary"`
	Labels      string `json:"labels"`
	Annotations string `json:"annotations"`
	Enabled     *bool  `json:"enabled"`
	ChangeLog   string `json:"change_log"`
}

type PrometheusRuleGroup struct {
	Name     string             `yaml:"name"`
	Rules    []PrometheusRule   `yaml:"rules"`
}

type PrometheusRule struct {
	Alert       string            `yaml:"alert,omitempty"`
	Expr        string            `yaml:"expr"`
	For         string            `yaml:"for,omitempty"`
	Labels      map[string]string `yaml:"labels,omitempty"`
	Annotations map[string]string `yaml:"annotations,omitempty"`
}

func (h *RuleHandler) List(c *gin.Context) {
	groupID := c.Query("group_id")
	var rules []models.AlertRule

	query := h.db.Preload("Group")
	if groupID != "" {
		query = query.Where("group_id = ?", groupID)
	}

	if err := query.Find(&rules).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, rules)
}

func (h *RuleHandler) Create(c *gin.Context) {
	var req CreateRuleRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if _, err := services.ValidatePromQL(req.Expr); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("Invalid PromQL: %v", err)})
		return
	}

	rule := models.AlertRule{
		GroupID:     req.GroupID,
		Name:        req.Name,
		Expr:        req.Expr,
		For:         req.For,
		Severity:    req.Severity,
		Description: req.Description,
		Summary:     req.Summary,
		Labels:      req.Labels,
		Annotations: req.Annotations,
		Enabled:     req.Enabled,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	tx := h.db.Begin()
	if err := tx.Create(&rule).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	version := models.AlertRuleVersion{
		RuleID:      rule.ID,
		Version:     1,
		Name:        rule.Name,
		Expr:        rule.Expr,
		For:         rule.For,
		Severity:    rule.Severity,
		Description: rule.Description,
		Summary:     rule.Summary,
		Labels:      rule.Labels,
		Annotations: rule.Annotations,
		ChangeLog:   req.ChangeLog,
		CreatedAt:   time.Now(),
	}

	if err := tx.Create(&version).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	tx.Commit()
	c.JSON(http.StatusCreated, rule)
}

func (h *RuleHandler) Get(c *gin.Context) {
	id := c.Param("id")
	var rule models.AlertRule
	if err := h.db.Preload("Group").Preload("Versions").First(&rule, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}
	c.JSON(http.StatusOK, rule)
}

func (h *RuleHandler) Update(c *gin.Context) {
	id := c.Param("id")
	var req UpdateRuleRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var rule models.AlertRule
	if err := h.db.First(&rule, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}

	if req.Expr != "" {
		if _, err := services.ValidatePromQL(req.Expr); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("Invalid PromQL: %v", err)})
			return
		}
	}

	tx := h.db.Begin()

	var maxVersion int
	tx.Model(&models.AlertRuleVersion{}).Where("rule_id = ?", id).Select("COALESCE(MAX(version), 0)").Scan(&maxVersion)
	newVersion := maxVersion + 1

	oldVersion := models.AlertRuleVersion{
		RuleID:      rule.ID,
		Version:     newVersion,
		Name:        rule.Name,
		Expr:        rule.Expr,
		For:         rule.For,
		Severity:    rule.Severity,
		Description: rule.Description,
		Summary:     rule.Summary,
		Labels:      rule.Labels,
		Annotations: rule.Annotations,
		ChangeLog:   req.ChangeLog,
		CreatedAt:   time.Now(),
	}

	if req.GroupID != "" {
		rule.GroupID = req.GroupID
	}
	if req.Name != "" {
		rule.Name = req.Name
	}
	if req.Expr != "" {
		rule.Expr = req.Expr
	}
	if req.For != "" {
		rule.For = req.For
	}
	if req.Severity != "" {
		rule.Severity = req.Severity
	}
	if req.Description != "" {
		rule.Description = req.Description
	}
	if req.Summary != "" {
		rule.Summary = req.Summary
	}
	if req.Labels != "" {
		rule.Labels = req.Labels
	}
	if req.Annotations != "" {
		rule.Annotations = req.Annotations
	}
	if req.Enabled != nil {
		rule.Enabled = *req.Enabled
	}
	rule.UpdatedAt = time.Now()

	if err := tx.Save(&rule).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := tx.Create(&oldVersion).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	tx.Commit()
	c.JSON(http.StatusOK, rule)
}

func (h *RuleHandler) Delete(c *gin.Context) {
	id := c.Param("id")
	tx := h.db.Begin()

	if err := tx.Where("rule_id = ?", id).Delete(&models.AlertRuleVersion{}).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	result := tx.Delete(&models.AlertRule{}, "id = ?", id)
	if result.Error != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": result.Error.Error()})
		return
	}
	if result.RowsAffected == 0 {
		tx.Rollback()
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}

	tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Rule deleted successfully"})
}

func (h *RuleHandler) ListVersions(c *gin.Context) {
	id := c.Param("id")
	var versions []models.AlertRuleVersion
	if err := h.db.Where("rule_id = ?", id).Order("version desc").Find(&versions).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, versions)
}

func (h *RuleHandler) RestoreVersion(c *gin.Context) {
	id := c.Param("id")
	versionId := c.Param("versionId")

	var version models.AlertRuleVersion
	if err := h.db.First(&version, "id = ? AND rule_id = ?", versionId, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Version not found"})
		return
	}

	var rule models.AlertRule
	if err := h.db.First(&rule, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}

	tx := h.db.Begin()

	var maxVersion int
	tx.Model(&models.AlertRuleVersion{}).Where("rule_id = ?", id).Select("COALESCE(MAX(version), 0)").Scan(&maxVersion)
	newVersion := maxVersion + 1

	newVersionRecord := models.AlertRuleVersion{
		RuleID:      rule.ID,
		Version:     newVersion,
		Name:        rule.Name,
		Expr:        rule.Expr,
		For:         rule.For,
		Severity:    rule.Severity,
		Description: rule.Description,
		Summary:     rule.Summary,
		Labels:      rule.Labels,
		Annotations: rule.Annotations,
		ChangeLog:   fmt.Sprintf("Restored from version %d", version.Version),
		CreatedAt:   time.Now(),
	}

	if err := tx.Create(&newVersionRecord).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	rule.Name = version.Name
	rule.Expr = version.Expr
	rule.For = version.For
	rule.Severity = version.Severity
	rule.Description = version.Description
	rule.Summary = version.Summary
	rule.Labels = version.Labels
	rule.Annotations = version.Annotations
	rule.UpdatedAt = time.Now()

	if err := tx.Save(&rule).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	tx.Commit()
	c.JSON(http.StatusOK, rule)
}

type VersionDiff struct {
	Field     string      `json:"field"`
	OldValue  interface{} `json:"old_value"`
	NewValue  interface{} `json:"new_value"`
	Changed   bool        `json:"changed"`
}

type CompareVersionsResponse struct {
	CurrentVersion  int            `json:"current_version"`
	TargetVersion   int            `json:"target_version"`
	Differences     []VersionDiff  `json:"differences"`
	ChangeCount     int            `json:"change_count"`
	PreviewRule     *models.AlertRule `json:"preview_rule"`
}

func (h *RuleHandler) CompareVersions(c *gin.Context) {
	id := c.Param("id")
	versionId := c.Param("versionId")

	var targetVersion models.AlertRuleVersion
	if err := h.db.First(&targetVersion, "id = ? AND rule_id = ?", versionId, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Version not found"})
		return
	}

	var currentRule models.AlertRule
	if err := h.db.First(&currentRule, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}

	var maxVersion int
	h.db.Model(&models.AlertRuleVersion{}).Where("rule_id = ?", id).Select("COALESCE(MAX(version), 0)").Scan(&maxVersion)

	previewRule := &models.AlertRule{
		ID:          currentRule.ID,
		GroupID:     currentRule.GroupID,
		Name:        targetVersion.Name,
		Expr:        targetVersion.Expr,
		For:         targetVersion.For,
		Severity:    targetVersion.Severity,
		Description: targetVersion.Description,
		Summary:     targetVersion.Summary,
		Labels:      targetVersion.Labels,
		Annotations: targetVersion.Annotations,
		Enabled:     currentRule.Enabled,
		CreatedAt:   currentRule.CreatedAt,
		UpdatedAt:   time.Now(),
	}

	differences := compareVersions(currentRule, targetVersion)

	changeCount := 0
	for _, d := range differences {
		if d.Changed {
			changeCount++
		}
	}

	c.JSON(http.StatusOK, CompareVersionsResponse{
		CurrentVersion: maxVersion,
		TargetVersion:  targetVersion.Version,
		Differences:    differences,
		ChangeCount:    changeCount,
		PreviewRule:    previewRule,
	})
}

type RestoreWithConfirmRequest struct {
	Confirm    bool   `json:"confirm" binding:"required"`
	ChangeLog  string `json:"change_log"`
}

func (h *RuleHandler) RestoreVersionWithConfirm(c *gin.Context) {
	id := c.Param("id")
	versionId := c.Param("versionId")

	var req RestoreWithConfirmRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if !req.Confirm {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Confirmation required to restore version"})
		return
	}

	var version models.AlertRuleVersion
	if err := h.db.First(&version, "id = ? AND rule_id = ?", versionId, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Version not found"})
		return
	}

	var currentRule models.AlertRule
	if err := h.db.First(&currentRule, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}

	tx := h.db.Begin()

	var maxVersion int
	tx.Model(&models.AlertRuleVersion{}).Where("rule_id = ?", id).Select("COALESCE(MAX(version), 0)").Scan(&maxVersion)
	newVersion := maxVersion + 1

	changeLog := req.ChangeLog
	if changeLog == "" {
		changeLog = fmt.Sprintf("Restored from version %d", version.Version)
	}

	newVersionRecord := models.AlertRuleVersion{
		RuleID:      currentRule.ID,
		Version:     newVersion,
		Name:        currentRule.Name,
		Expr:        currentRule.Expr,
		For:         currentRule.For,
		Severity:    currentRule.Severity,
		Description: currentRule.Description,
		Summary:     currentRule.Summary,
		Labels:      currentRule.Labels,
		Annotations: currentRule.Annotations,
		ChangeLog:   changeLog,
		CreatedAt:   time.Now(),
	}

	if err := tx.Create(&newVersionRecord).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	currentRule.Name = version.Name
	currentRule.Expr = version.Expr
	currentRule.For = version.For
	currentRule.Severity = version.Severity
	currentRule.Description = version.Description
	currentRule.Summary = version.Summary
	currentRule.Labels = version.Labels
	currentRule.Annotations = version.Annotations
	currentRule.UpdatedAt = time.Now()

	if err := tx.Save(&currentRule).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	tx.Commit()

	differences := compareVersions(currentRule, version)

	c.JSON(http.StatusOK, gin.H{
		"message": fmt.Sprintf("Successfully restored to version %d", version.Version),
		"rule":    currentRule,
		"version": newVersion,
		"changes": differences,
	})
}

func compareVersions(rule models.AlertRule, version models.AlertRuleVersion) []VersionDiff {
	fields := []struct {
		name   string
		oldVal interface{}
		newVal interface{}
	}{
		{"name", rule.Name, version.Name},
		{"expr", rule.Expr, version.Expr},
		{"for", rule.For, version.For},
		{"severity", rule.Severity, version.Severity},
		{"description", rule.Description, version.Description},
		{"summary", rule.Summary, version.Summary},
		{"labels", rule.Labels, version.Labels},
		{"annotations", rule.Annotations, version.Annotations},
	}

	var differences []VersionDiff
	for _, f := range fields {
		changed := !reflect.DeepEqual(f.oldVal, f.newVal)
		differences = append(differences, VersionDiff{
			Field:     f.name,
			OldValue:  f.oldVal,
			NewValue:  f.newVal,
			Changed:   changed,
		})
	}

	return differences
}

func (h *RuleHandler) Import(c *gin.Context) {
	format := c.DefaultQuery("format", "yaml")
	groupID := c.Query("group_id")

	var rules []models.AlertRule

	if format == "json" {
		if err := c.ShouldBindJSON(&rules); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
	} else {
		var buf bytes.Buffer
		if _, err := buf.ReadFrom(c.Request.Body); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		var groups []PrometheusRuleGroup
		if err := yaml.Unmarshal(buf.Bytes(), &groups); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("Invalid YAML: %v", err)})
			return
		}

		for _, pg := range groups {
			gid := groupID
			if gid == "" {
				var group models.AlertGroup
				if err := h.db.Where("name = ?", pg.Name).First(&group).Error; err != nil {
					group = models.AlertGroup{
						Name:        pg.Name,
						Description: fmt.Sprintf("Imported from Prometheus rules"),
						CreatedAt:   time.Now(),
						UpdatedAt:   time.Now(),
					}
					if err := h.db.Create(&group).Error; err != nil {
						c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
						return
					}
				}
				gid = group.ID
			}

			for _, pr := range pg.Rules {
				labelsJSON, _ := json.Marshal(pr.Labels)
				annotationsJSON, _ := json.Marshal(pr.Annotations)

				severity := pr.Labels["severity"]
				summary := pr.Annotations["summary"]
				description := pr.Annotations["description"]

				rule := models.AlertRule{
					GroupID:     gid,
					Name:        pr.Alert,
					Expr:        pr.Expr,
					For:         pr.For,
					Severity:    severity,
					Description: description,
					Summary:     summary,
					Labels:      string(labelsJSON),
					Annotations: string(annotationsJSON),
					Enabled:     true,
					CreatedAt:   time.Now(),
					UpdatedAt:   time.Now(),
				}

				if _, err := services.ValidatePromQL(rule.Expr); err != nil {
					c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("Invalid PromQL in rule '%s': %v", rule.Name, err)})
					return
				}

				rules = append(rules, rule)
			}
		}
	}

	tx := h.db.Begin()
	for i := range rules {
		if err := tx.Create(&rules[i]).Error; err != nil {
			tx.Rollback()
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		version := models.AlertRuleVersion{
			RuleID:      rules[i].ID,
			Version:     1,
			Name:        rules[i].Name,
			Expr:        rules[i].Expr,
			For:         rules[i].For,
			Severity:    rules[i].Severity,
			Description: rules[i].Description,
			Summary:     rules[i].Summary,
			Labels:      rules[i].Labels,
			Annotations: rules[i].Annotations,
			ChangeLog:   "Imported",
			CreatedAt:   time.Now(),
		}

		if err := tx.Create(&version).Error; err != nil {
			tx.Rollback()
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
	}
	tx.Commit()

	c.JSON(http.StatusCreated, gin.H{"message": fmt.Sprintf("Successfully imported %d rules", len(rules)), "count": len(rules)})
}

func (h *RuleHandler) Export(c *gin.Context) {
	format := c.DefaultQuery("format", "yaml")
	groupID := c.Query("group_id")

	var rules []models.AlertRule
	query := h.db.Preload("Group")
	if groupID != "" {
		query = query.Where("group_id = ?", groupID)
	}
	if err := query.Find(&rules).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if format == "json" {
		c.JSON(http.StatusOK, rules)
		return
	}

	groupsMap := make(map[string][]PrometheusRule)
	for _, r := range rules {
		groupName := "default"
		if r.Group.Name != "" {
			groupName = r.Group.Name
		}

		var labels map[string]string
		var annotations map[string]string
		json.Unmarshal([]byte(r.Labels), &labels)
		json.Unmarshal([]byte(r.Annotations), &annotations)

		if labels == nil {
			labels = make(map[string]string)
		}
		if r.Severity != "" {
			labels["severity"] = r.Severity
		}

		if annotations == nil {
			annotations = make(map[string]string)
		}
		if r.Summary != "" {
			annotations["summary"] = r.Summary
		}
		if r.Description != "" {
			annotations["description"] = r.Description
		}

		pr := PrometheusRule{
			Alert:       r.Name,
			Expr:        r.Expr,
			For:         r.For,
			Labels:      labels,
			Annotations: annotations,
		}

		groupsMap[groupName] = append(groupsMap[groupName], pr)
	}

	var groups []PrometheusRuleGroup
	for name, rules := range groupsMap {
		groups = append(groups, PrometheusRuleGroup{
			Name:  name,
			Rules: rules,
		})
	}

	yamlData, err := yaml.Marshal(groups)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.Header("Content-Type", "application/x-yaml")
	c.Header("Content-Disposition", "attachment; filename=alert_rules.yaml")
	c.String(http.StatusOK, string(yamlData))
}

package api

import (
	"cloud-tag-compliance/internal/audit"
	"cloud-tag-compliance/internal/auth"
	"cloud-tag-compliance/internal/cloud"
	"cloud-tag-compliance/internal/config"
	"cloud-tag-compliance/internal/cost"
	"cloud-tag-compliance/internal/nlparser"
	"cloud-tag-compliance/internal/rules"
	"cloud-tag-compliance/internal/suggestion"
	"cloud-tag-compliance/internal/templates"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	cloudManager     *cloud.Manager
	ruleEngine       *rules.Engine
	config           *config.Config
	trustManager     *auth.TrustManager
	suggestionEngine *suggestion.SuggestionEngine
	nlParser         *nlparser.NLParser
	costEngine       *cost.AllocationEngine
	auditLogger      *audit.AuditLogger
	templateManager  *templates.TemplateManager
}

func SetupRouter(cloudManager *cloud.Manager, ruleEngine *rules.Engine, cfg *config.Config,
	trustManager *auth.TrustManager, suggestionEngine *suggestion.SuggestionEngine, nlParser *nlparser.NLParser,
	costEngine *cost.AllocationEngine, auditLogger *audit.AuditLogger, templateManager *templates.TemplateManager) *gin.Engine {
	gin.SetMode(cfg.Server.Mode)
	router := gin.Default()

	router.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-ID")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	})

	handler := &Handler{
		cloudManager:     cloudManager,
		ruleEngine:       ruleEngine,
		config:           cfg,
		trustManager:     trustManager,
		suggestionEngine: suggestionEngine,
		nlParser:         nlParser,
		costEngine:       costEngine,
		auditLogger:      auditLogger,
		templateManager:  templateManager,
	}

	api := router.Group("/api/v1")
	{
		api.GET("/health", handler.healthCheck)

		authGroup := api.Group("/auth")
		{
			authGroup.POST("/login", handler.login)
			authGroup.POST("/switch-role", handler.switchRole)
			authGroup.POST("/switch-account", handler.switchAccount)
			authGroup.POST("/seamless-switch", handler.seamlessSwitch)
			authGroup.GET("/roles", handler.getRoles)
			authGroup.GET("/trust-chains", handler.getTrustChains)
			authGroup.GET("/session/:id", handler.getSession)
			authGroup.GET("/available-accounts", handler.getAvailableAccounts)
			authGroup.GET("/available-roles", handler.getAvailableRoles)
		}

		accounts := api.Group("/accounts")
		{
			accounts.GET("", handler.getAccounts)
		}

		resources := api.Group("/resources")
		{
			resources.GET("", handler.getResources)
			resources.GET("/:id/suggestions", handler.getTagSuggestions)
			resources.GET("/:id/smart-suggestions", handler.getSmartTagSuggestions)
			resources.POST("/batch-suggestions", handler.getBatchTagSuggestions)
			resources.GET("/:id/matching-templates", handler.getMatchingTemplates)
			resources.POST("/:id/apply-template", handler.applyTemplateToResource)
		}

		rulesGroup := api.Group("/rules")
		{
			rulesGroup.GET("", handler.getRules)
			rulesGroup.POST("", handler.createRule)
			rulesGroup.PUT("/:id", handler.updateRule)
			rulesGroup.DELETE("/:id", handler.deleteRule)
			rulesGroup.POST("/parse-natural", handler.parseNaturalRule)
			rulesGroup.GET("/templates", handler.getRuleTemplates)
		}

		compliance := api.Group("/compliance")
		{
			compliance.GET("", handler.checkCompliance)
			compliance.GET("/summary", handler.getComplianceSummary)
		}

		costGroup := api.Group("/cost")
		{
			costGroup.GET("/report", handler.getCostReport)
			costGroup.GET("/by-tag/:tagKey", handler.getCostByTag)
			costGroup.GET("/resource/:id", handler.getResourceCost)
			costGroup.GET("/trend", handler.getCostTrend)
			costGroup.GET("/forecast", handler.getCostForecast)
		}

		auditGroup := api.Group("/audit")
		{
			auditGroup.GET("", handler.getAuditLogs)
			auditGroup.GET("/resource/:id", handler.getResourceAuditLogs)
			auditGroup.GET("/statistics", handler.getAuditStatistics)
			auditGroup.GET("/export", handler.exportAuditLogs)
			auditGroup.POST("/log", handler.createAuditLog)
		}

		templateGroup := api.Group("/tag-templates")
		{
			templateGroup.GET("", handler.getTagTemplates)
			templateGroup.GET("/:id", handler.getTagTemplate)
			templateGroup.POST("", handler.createTagTemplate)
			templateGroup.PUT("/:id", handler.updateTagTemplate)
			templateGroup.DELETE("/:id", handler.deleteTagTemplate)
			templateGroup.POST("/:id/apply", handler.applyTagTemplate)
			templateGroup.GET("/match/:resourceId", handler.getMatchingTemplatesForResource)
		}
	}

	return router
}

func (h *Handler) healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ok",
	})
}

func (h *Handler) getAccounts(c *gin.Context) {
	accounts := h.cloudManager.GetAccounts()
	c.JSON(http.StatusOK, gin.H{
		"data": accounts,
	})
}

func (h *Handler) getResources(c *gin.Context) {
	accountID := c.Query("accountId")
	resourceType := c.Query("type")

	var resources []cloud.Resource
	if accountID != "" {
		resources = h.cloudManager.GetResourcesByAccount(accountID)
	} else {
		resources = h.cloudManager.GetAllResources()
	}

	if resourceType != "" {
		var filtered []cloud.Resource
		for _, r := range resources {
			if string(r.Type) == resourceType {
				filtered = append(filtered, r)
			}
		}
		resources = filtered
	}

	c.JSON(http.StatusOK, gin.H{
		"data":  resources,
		"total": len(resources),
	})
}

func (h *Handler) getTagSuggestions(c *gin.Context) {
	resourceID := c.Param("id")

	resources := h.cloudManager.GetAllResources()
	var targetResource *cloud.Resource
	for i := range resources {
		if resources[i].ID == resourceID {
			targetResource = &resources[i]
			break
		}
	}

	if targetResource == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Resource not found",
		})
		return
	}

	suggestions := h.ruleEngine.GetTagSuggestions(*targetResource)

	c.JSON(http.StatusOK, gin.H{
		"resourceId":  resourceID,
		"currentTags": targetResource.Tags,
		"suggestions": suggestions,
	})
}

func (h *Handler) getRules(c *gin.Context) {
	rulesList := h.ruleEngine.GetRules()
	c.JSON(http.StatusOK, gin.H{
		"data": rulesList,
	})
}

func (h *Handler) createRule(c *gin.Context) {
	var rule rules.Rule
	if err := c.ShouldBindJSON(&rule); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}

	h.ruleEngine.AddRule(rule)
	c.JSON(http.StatusCreated, gin.H{
		"data": rule,
	})
}

func (h *Handler) updateRule(c *gin.Context) {
	id := c.Param("id")
	var updatedRule rules.Rule
	if err := c.ShouldBindJSON(&updatedRule); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}

	rulesList := h.ruleEngine.GetRules()
	for i := range rulesList {
		if rulesList[i].ID == id {
			rulesList[i] = updatedRule
			c.JSON(http.StatusOK, gin.H{
				"data": updatedRule,
			})
			return
		}
	}

	c.JSON(http.StatusNotFound, gin.H{
		"error": "Rule not found",
	})
}

func (h *Handler) deleteRule(c *gin.Context) {
	id := c.Param("id")
	rulesList := h.ruleEngine.GetRules()
	for i := range rulesList {
		if rulesList[i].ID == id {
			h.ruleEngine.GetRules()[i].Enabled = false
			c.JSON(http.StatusOK, gin.H{
				"message": "Rule disabled",
			})
			return
		}
	}

	c.JSON(http.StatusNotFound, gin.H{
		"error": "Rule not found",
	})
}

func (h *Handler) checkCompliance(c *gin.Context) {
	accountID := c.Query("accountId")
	resourceType := c.Query("type")

	var resources []cloud.Resource
	if accountID != "" {
		resources = h.cloudManager.GetResourcesByAccount(accountID)
	} else {
		resources = h.cloudManager.GetAllResources()
	}

	if resourceType != "" {
		var filtered []cloud.Resource
		for _, r := range resources {
			if string(r.Type) == resourceType {
				filtered = append(filtered, r)
			}
		}
		resources = filtered
	}

	result := h.ruleEngine.CheckResources(resources)
	c.JSON(http.StatusOK, result)
}

func (h *Handler) getComplianceSummary(c *gin.Context) {
	resources := h.cloudManager.GetAllResources()
	result := h.ruleEngine.CheckResources(resources)

	violationsByType := make(map[string]int)
	violationsBySeverity := make(map[string]int)
	violationsByAccount := make(map[string]int)

	for _, v := range result.Violations {
		violationsByType[string(v.ResourceType)]++
		violationsBySeverity[v.Severity]++
		violationsByAccount[v.AccountName]++
	}

	c.JSON(http.StatusOK, gin.H{
		"summary": gin.H{
			"totalResources":   result.TotalResources,
			"compliant":        result.Compliant,
			"nonCompliant":     result.NonCompliant,
			"complianceRate":   result.ComplianceRate,
			"totalViolations":  len(result.Violations),
		},
		"violationsByType":     violationsByType,
		"violationsBySeverity": violationsBySeverity,
		"violationsByAccount":  violationsByAccount,
	})
}

func (h *Handler) login(c *gin.Context) {
	var req struct {
		Username string `json:"username"`
		Password string `json:"password"`
		RoleID   string `json:"roleId"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	session, err := h.trustManager.Login(req.Username, req.Password, req.RoleID)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"sessionId": session.ID,
		"token":     session.Token,
		"role":      session.Role,
		"account":   session.Account,
		"expiresAt": session.ExpiresAt,
	})
}

func (h *Handler) switchRole(c *gin.Context) {
	var req struct {
		SessionID string `json:"sessionId"`
		NewRoleID string `json:"newRoleId"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	session, err := h.trustManager.SwitchRole(req.SessionID, req.NewRoleID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"sessionId": session.ID,
		"token":     session.Token,
		"role":      session.Role,
		"account":   session.Account,
		"expiresAt": session.ExpiresAt,
	})
}

func (h *Handler) switchAccount(c *gin.Context) {
	var req struct {
		SessionID        string `json:"sessionId"`
		TargetAccountID  string `json:"targetAccountId"`
		TargetRoleID     string `json:"targetRoleId"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	session, err := h.trustManager.SwitchAccount(req.SessionID, req.TargetAccountID, req.TargetRoleID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"sessionId": session.ID,
		"token":     session.Token,
		"role":      session.Role,
		"account":   session.Account,
		"expiresAt": session.ExpiresAt,
	})
}

func (h *Handler) seamlessSwitch(c *gin.Context) {
	var req struct {
		SessionID       string `json:"sessionId"`
		TargetAccountID string `json:"targetAccountId"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	session, err := h.trustManager.SeamlessSwitch(req.SessionID, req.TargetAccountID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"sessionId": session.ID,
		"token":     session.Token,
		"role":      session.Role,
		"account":   session.Account,
		"expiresAt": session.ExpiresAt,
		"trustPath": session.TrustPath,
	})
}

func (h *Handler) getRoles(c *gin.Context) {
	roles := h.trustManager.GetAllRoles()
	c.JSON(http.StatusOK, gin.H{"data": roles})
}

func (h *Handler) getTrustChains(c *gin.Context) {
	chains := h.trustManager.GetAllTrustChains()
	c.JSON(http.StatusOK, gin.H{"data": chains})
}

func (h *Handler) getSession(c *gin.Context) {
	sessionID := c.Param("id")
	session, valid := h.trustManager.GetSession(sessionID)
	if !valid {
		c.JSON(http.StatusNotFound, gin.H{"error": "Session not found or expired"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"data": session})
}

func (h *Handler) getAvailableAccounts(c *gin.Context) {
	sessionID := c.GetHeader("X-Session-ID")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Session ID required"})
		return
	}

	accounts := h.trustManager.GetAvailableAccounts(sessionID)
	c.JSON(http.StatusOK, gin.H{"data": accounts})
}

func (h *Handler) getAvailableRoles(c *gin.Context) {
	sessionID := c.GetHeader("X-Session-ID")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Session ID required"})
		return
	}

	roles := h.trustManager.GetAvailableRoles(sessionID)
	c.JSON(http.StatusOK, gin.H{"data": roles})
}

func (h *Handler) getSmartTagSuggestions(c *gin.Context) {
	resourceID := c.Param("id")

	resources := h.cloudManager.GetAllResources()
	var targetResource *cloud.Resource
	for i := range resources {
		if resources[i].ID == resourceID {
			targetResource = &resources[i]
			break
		}
	}

	if targetResource == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Resource not found"})
		return
	}

	suggestions := h.suggestionEngine.SuggestTags(targetResource.Name, string(targetResource.Type), targetResource.Tags)

	c.JSON(http.StatusOK, gin.H{
		"resourceId":   resourceID,
		"resourceName": targetResource.Name,
		"resourceType": targetResource.Type,
		"currentTags":  targetResource.Tags,
		"suggestions":  suggestions,
	})
}

func (h *Handler) getBatchTagSuggestions(c *gin.Context) {
	var req struct {
		ResourceIDs []string `json:"resourceIds"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	resources := h.cloudManager.GetAllResources()
	resourceMap := make(map[string]*cloud.Resource)
	for i := range resources {
		resourceMap[resources[i].ID] = &resources[i]
	}

	results := make([]map[string]interface{}, 0)
	for _, id := range req.ResourceIDs {
		if r, ok := resourceMap[id]; ok {
			suggestions := h.suggestionEngine.SuggestTags(r.Name, string(r.Type), r.Tags)
			results = append(results, map[string]interface{}{
				"resourceId":   id,
				"resourceName": r.Name,
				"suggestions":  suggestions,
			})
		}
	}

	c.JSON(http.StatusOK, gin.H{"data": results, "total": len(results)})
}

func (h *Handler) parseNaturalRule(c *gin.Context) {
	var req struct {
		Text string `json:"text"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := h.nlParser.Parse(req.Text)

	if !result.Success {
		c.JSON(http.StatusOK, gin.H{
			"success":        false,
			"interpretation": result.Interpretation,
			"confidence":     result.Confidence,
			"warning":        result.Warning,
		})
		return
	}

	valid, validationMsg := h.ruleEngine.ValidateRule(*result.Rule)

	c.JSON(http.StatusOK, gin.H{
		"success":        result.Success,
		"rule":           result.Rule,
		"interpretation": result.Interpretation,
		"confidence":     result.Confidence,
		"isValid":        valid,
		"validationMsg":  validationMsg,
		"warning":        result.Warning,
	})
}

func (h *Handler) getRuleTemplates(c *gin.Context) {
	templates := []map[string]string{
		{
			"name":        "必填标签",
			"example":     "所有资源必须包含 Environment 标签",
			"type":        string(rules.RequiredTag),
			"description": "指定标签必须存在于所有资源上",
		},
		{
			"name":        "禁用标签",
			"example":     "禁止使用 Owner 标签",
			"type":        string(rules.ForbiddenTag),
			"description": "指定标签不允许存在",
		},
		{
			"name":        "标签值枚举",
			"example":     "Environment 标签的值必须是 [Production, Development] 之一",
			"type":        string(rules.TagValueInList),
			"description": "标签值必须在指定列表中",
		},
		{
			"name":        "标签值正则",
			"example":     "CostCenter 标签的值必须匹配正则 ^CC\\d{3}$",
			"type":        string(rules.TagValueRegex),
			"description": "标签值必须匹配指定正则表达式",
		},
		{
			"name":        "大小写敏感",
			"example":     "Environment 标签的值大小写敏感",
			"type":        string(rules.CaseSensitive),
			"description": "标签值比较时区分大小写",
		},
	}

	c.JSON(http.StatusOK, gin.H{"data": templates})
}

func (h *Handler) getCostReport(c *gin.Context) {
	resources := h.cloudManager.GetAllResources()
	report := h.costEngine.GenerateReport(resources)
	c.JSON(http.StatusOK, gin.H{"data": report})
}

func (h *Handler) getCostByTag(c *gin.Context) {
	tagKey := c.Param("tagKey")
	resources := h.cloudManager.GetAllResources()
	report := h.costEngine.GenerateReport(resources)

	var summary interface{}
	switch tagKey {
	case "Environment":
		summary = report.ByEnvironment
	case "Department":
		summary = report.ByDepartment
	case "CostCenter":
		summary = report.ByCostCenter
	case "Project":
		summary = report.ByProject
	default:
		if summaries, ok := report.ByTag[tagKey]; ok {
			summary = summaries
		} else {
			summary = []interface{}{}
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"tagKey": tagKey,
		"data":   summary,
	})
}

func (h *Handler) getResourceCost(c *gin.Context) {
	resourceID := c.Param("id")
	resources := h.cloudManager.GetAllResources()

	var targetResource *cloud.Resource
	for i := range resources {
		if resources[i].ID == resourceID {
			targetResource = &resources[i]
			break
		}
	}

	if targetResource == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Resource not found"})
		return
	}

	costs := h.costEngine.CalculateCosts([]cloud.Resource{*targetResource})
	if len(costs) > 0 {
		c.JSON(http.StatusOK, gin.H{"data": costs[0]})
	} else {
		c.JSON(http.StatusNotFound, gin.H{"error": "Cost not calculated"})
	}
}

func (h *Handler) getCostTrend(c *gin.Context) {
	days := 7
	if d := c.Query("days"); d != "" {
		if n, err := strconv.Atoi(d); err == nil && n > 0 {
			days = n
		}
	}

	resources := h.cloudManager.GetAllResources()
	trend := h.costEngine.GetCostTrend(resources, days)

	c.JSON(http.StatusOK, gin.H{
		"days": days,
		"data": trend,
	})
}

func (h *Handler) getCostForecast(c *gin.Context) {
	months := 3
	if m := c.Query("months"); m != "" {
		if n, err := strconv.Atoi(m); err == nil && n > 0 {
			months = n
		}
	}

	resources := h.cloudManager.GetAllResources()
	forecast := h.costEngine.GetCostForecast(resources, months)

	c.JSON(http.StatusOK, gin.H{
		"months": months,
		"data":   forecast,
	})
}

func (h *Handler) getAuditLogs(c *gin.Context) {
	resourceID := c.Query("resourceId")
	action := c.Query("action")
	operator := c.Query("operator")
	startDate := c.Query("startDate")
	endDate := c.Query("endDate")
	limit := 100
	if l := c.Query("limit"); l != "" {
		if n, err := strconv.Atoi(l); err == nil && n > 0 {
			limit = n
		}
	}

	logs := h.auditLogger.Query(resourceID, action, operator, startDate, endDate, limit)
	c.JSON(http.StatusOK, gin.H{"data": logs, "total": len(logs)})
}

func (h *Handler) getResourceAuditLogs(c *gin.Context) {
	resourceID := c.Param("id")
	logs := h.auditLogger.GetByResource(resourceID)
	c.JSON(http.StatusOK, gin.H{"data": logs, "total": len(logs)})
}

func (h *Handler) getAuditStatistics(c *gin.Context) {
	stats := h.auditLogger.GetStatistics()
	c.JSON(http.StatusOK, gin.H{"data": stats})
}

func (h *Handler) exportAuditLogs(c *gin.Context) {
	startDate := c.Query("startDate")
	endDate := c.Query("endDate")

	data, err := h.auditLogger.Export(startDate, endDate)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.Header("Content-Type", "application/json")
	c.Header("Content-Disposition", "attachment; filename=audit_logs.json")
	c.Writer.Write(data)
}

func (h *Handler) createAuditLog(c *gin.Context) {
	var entry audit.AuditLogEntry
	if err := c.ShouldBindJSON(&entry); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.auditLogger.Log(entry)
	c.JSON(http.StatusCreated, gin.H{"message": "Log created"})
}

func (h *Handler) getTagTemplates(c *gin.Context) {
	templates := h.templateManager.GetAll()
	c.JSON(http.StatusOK, gin.H{"data": templates, "total": len(templates)})
}

func (h *Handler) getTagTemplate(c *gin.Context) {
	id := c.Param("id")
	template, ok := h.templateManager.Get(id)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "Template not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"data": template})
}

func (h *Handler) createTagTemplate(c *gin.Context) {
	var template templates.TagTemplate
	if err := c.ShouldBindJSON(&template); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.templateManager.Create(template)
	c.JSON(http.StatusCreated, gin.H{"message": "Template created"})
}

func (h *Handler) updateTagTemplate(c *gin.Context) {
	id := c.Param("id")
	var template templates.TagTemplate
	if err := c.ShouldBindJSON(&template); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	template.ID = id
	h.templateManager.Update(template)
	c.JSON(http.StatusOK, gin.H{"message": "Template updated"})
}

func (h *Handler) deleteTagTemplate(c *gin.Context) {
	id := c.Param("id")
	h.templateManager.Delete(id)
	c.JSON(http.StatusOK, gin.H{"message": "Template deleted"})
}

func (h *Handler) applyTagTemplate(c *gin.Context) {
	id := c.Param("id")
	template, ok := h.templateManager.Get(id)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "Template not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Tags extracted from template",
		"tags":    template.Tags,
	})
}

func (h *Handler) getMatchingTemplatesForResource(c *gin.Context) {
	resourceID := c.Param("resourceId")
	resources := h.cloudManager.GetAllResources()

	var targetResource *cloud.Resource
	for i := range resources {
		if resources[i].ID == resourceID {
			targetResource = &resources[i]
			break
		}
	}

	if targetResource == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Resource not found"})
		return
	}

	matched := h.templateManager.MatchTemplates(*targetResource)
	c.JSON(http.StatusOK, gin.H{
		"data":     matched,
		"total":    len(matched),
		"resource": targetResource.Name,
	})
}

func (h *Handler) getMatchingTemplates(c *gin.Context) {
	resourceID := c.Param("id")
	resources := h.cloudManager.GetAllResources()

	var targetResource *cloud.Resource
	for i := range resources {
		if resources[i].ID == resourceID {
			targetResource = &resources[i]
			break
		}
	}

	if targetResource == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Resource not found"})
		return
	}

	matched := h.templateManager.MatchTemplates(*targetResource)
	c.JSON(http.StatusOK, gin.H{
		"data":     matched,
		"total":    len(matched),
		"resource": targetResource.Name,
	})
}

func (h *Handler) applyTemplateToResource(c *gin.Context) {
	resourceID := c.Param("id")
	var req struct {
		TemplateID string `json:"templateId"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	tags, ok := h.templateManager.ApplyTemplateToResource(resourceID, req.TemplateID)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "Template not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Template applied",
		"tags":    tags,
	})
}

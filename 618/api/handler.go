package api

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"nacos-audit-tool/models"
	"nacos-audit-tool/service"
)

type Handler struct {
	auditService *service.AuditService
}

func NewHandler(auditService *service.AuditService) *Handler {
	return &Handler{
		auditService: auditService,
	}
}

type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

func (h *Handler) GetAuditLogs(c *gin.Context) {
	namespaceID := c.Query("namespace_id")
	group := c.Query("group")
	dataID := c.Query("data_id")
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))

	logs, total, err := h.auditService.GetAuditLogs(namespaceID, group, dataID, page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data: gin.H{
			"list":  logs,
			"total": total,
			"page":  page,
			"page_size": pageSize,
		},
	})
}

func (h *Handler) GetAuditLog(c *gin.Context) {
	id := c.Param("id")

	log, err := h.auditService.GetAuditLog(id)
	if err != nil {
		c.JSON(http.StatusNotFound, Response{
			Code:    404,
			Message: "Audit log not found",
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    log,
	})
}

func (h *Handler) GetDiff(c *gin.Context) {
	id := c.Param("id")

	diffResult, err := h.auditService.GetDiff(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    diffResult,
	})
}

func (h *Handler) GetStructDiff(c *gin.Context) {
	id := c.Param("id")

	diffResult, err := h.auditService.GetStructDiff(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    diffResult,
	})
}

type RollbackRequest struct {
	Operator string `json:"operator" binding:"required"`
}

func (h *Handler) Rollback(c *gin.Context) {
	id := c.Param("id")

	var req RollbackRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	log, err := h.auditService.Rollback(id, req.Operator)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Rollback successful",
		Data:    log,
	})
}

type RecordChangeRequest struct {
	NamespaceID string `json:"namespace_id" binding:"required"`
	Group       string `json:"group" binding:"required"`
	DataID      string `json:"data_id" binding:"required"`
	Operator    string `json:"operator" binding:"required"`
	OperatorIP  string `json:"operator_ip"`
	OldContent  string `json:"old_content"`
	NewContent  string `json:"new_content" binding:"required"`
	Desc        string `json:"desc"`
}

func (h *Handler) RecordChange(c *gin.Context) {
	var req RecordChangeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	log, err := h.auditService.RecordChange(
		req.NamespaceID,
		req.Group,
		req.DataID,
		req.Operator,
		req.OperatorIP,
		req.OldContent,
		req.NewContent,
		req.Desc,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Record created successfully",
		Data:    log,
	})
}

func (h *Handler) GetNamespaces(c *gin.Context) {
	namespaces, err := h.auditService.GetNamespaces()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    namespaces,
	})
}

func (h *Handler) GetNamespaceConfigs(c *gin.Context) {
	configs, err := h.auditService.GetNamespaceConfigs()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    configs,
	})
}

func (h *Handler) SaveNamespaceConfig(c *gin.Context) {
	var config models.NamespaceConfig
	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	err := h.auditService.SaveNamespaceConfig(&config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Config saved successfully",
		Data:    config,
	})
}

func (h *Handler) GetComplianceRules(c *gin.Context) {
	rules, err := h.auditService.GetComplianceRules()
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    rules,
	})
}

func (h *Handler) SaveComplianceRule(c *gin.Context) {
	var rule models.ComplianceRule
	if err := c.ShouldBindJSON(&rule); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	err := h.auditService.SaveComplianceRule(&rule)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Rule saved successfully",
		Data:    rule,
	})
}

func (h *Handler) DeleteComplianceRule(c *gin.Context) {
	id := c.Param("id")

	err := h.auditService.DeleteComplianceRule(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Rule deleted successfully",
	})
}

type ListenerRequest struct {
	NamespaceID string `json:"namespace_id" binding:"required"`
	Group       string `json:"group" binding:"required"`
	DataID      string `json:"data_id" binding:"required"`
}

func (h *Handler) StartListener(c *gin.Context) {
	var req ListenerRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	err := h.auditService.StartConfigListener(req.NamespaceID, req.Group, req.DataID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Listener started successfully",
	})
}

func (h *Handler) StopListener(c *gin.Context) {
	var req ListenerRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	err := h.auditService.StopConfigListener(req.NamespaceID, req.Group, req.DataID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Listener stopped successfully",
	})
}

func (h *Handler) AnalyzeImpact(c *gin.Context) {
	namespaceID := c.Query("namespace_id")
	group := c.Query("group")
	dataID := c.Query("data_id")

	if namespaceID == "" || group == "" || dataID == "" {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "namespace_id, group and data_id are required",
		})
		return
	}

	analysis, err := h.auditService.AnalyzeImpact(namespaceID, group, dataID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    analysis,
	})
}

type QuickRollbackRequest struct {
	NamespaceID string `json:"namespace_id" binding:"required"`
	Group       string `json:"group" binding:"required"`
	DataID      string `json:"data_id" binding:"required"`
	Operator    string `json:"operator" binding:"required"`
}

func (h *Handler) QuickRollback(c *gin.Context) {
	var req QuickRollbackRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	log, err := h.auditService.QuickRollback(req.NamespaceID, req.Group, req.DataID, req.Operator)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Quick rollback successful",
		Data:    log,
	})
}

func (h *Handler) GetDashboard(c *gin.Context) {
	days, _ := strconv.Atoi(c.DefaultQuery("days", "30"))

	stats, err := h.auditService.GetDashboardStats(days)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    stats,
	})
}

func (h *Handler) GetServiceRegistries(c *gin.Context) {
	namespaceID := c.Query("namespace_id")
	group := c.Query("group")
	dataID := c.Query("data_id")

	services, err := h.auditService.GetServiceRegistries(namespaceID, group, dataID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    services,
	})
}

func (h *Handler) CreateServiceRegistry(c *gin.Context) {
	var svc models.ServiceRegistry
	if err := c.ShouldBindJSON(&svc); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	err := h.auditService.CreateServiceRegistry(&svc)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Service registered successfully",
		Data:    svc,
	})
}

func (h *Handler) UpdateServiceRegistry(c *gin.Context) {
	var svc models.ServiceRegistry
	if err := c.ShouldBindJSON(&svc); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	err := h.auditService.UpdateServiceRegistry(&svc)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Service updated successfully",
		Data:    svc,
	})
}

func (h *Handler) DeleteServiceRegistry(c *gin.Context) {
	id := c.Param("id")

	err := h.auditService.DeleteServiceRegistry(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Service deleted successfully",
	})
}

func (h *Handler) GetRollbackPolicies(c *gin.Context) {
	namespaceID := c.Query("namespace_id")

	policies, err := h.auditService.GetRollbackPolicies(namespaceID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "success",
		Data:    policies,
	})
}

func (h *Handler) CreateRollbackPolicy(c *gin.Context) {
	var policy models.RollbackPolicy
	if err := c.ShouldBindJSON(&policy); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	err := h.auditService.CreateRollbackPolicy(&policy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Policy created successfully",
		Data:    policy,
	})
}

func (h *Handler) UpdateRollbackPolicy(c *gin.Context) {
	var policy models.RollbackPolicy
	if err := c.ShouldBindJSON(&policy); err != nil {
		c.JSON(http.StatusBadRequest, Response{
			Code:    400,
			Message: "Invalid request: " + err.Error(),
		})
		return
	}

	err := h.auditService.UpdateRollbackPolicy(&policy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Policy updated successfully",
		Data:    policy,
	})
}

func (h *Handler) DeleteRollbackPolicy(c *gin.Context) {
	id := c.Param("id")

	err := h.auditService.DeleteRollbackPolicy(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, Response{
			Code:    500,
			Message: err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, Response{
		Code:    200,
		Message: "Policy deleted successfully",
	})
}

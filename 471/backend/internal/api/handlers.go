package api

import (
	"context"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
	"gorm.io/gorm"

	"github.com/keymgmt/service/backend/internal/audit"
	"github.com/keymgmt/service/backend/internal/compliance"
	"github.com/keymgmt/service/backend/internal/models"
	"github.com/keymgmt/service/backend/internal/recovery"
	"github.com/keymgmt/service/backend/internal/version"
	"github.com/keymgmt/service/backend/internal/vault"
	"github.com/keymgmt/service/backend/pkg/utils"
)

type SecretHandler struct {
	db           *gorm.DB
	vaultClient  *vault.VaultClient
	auditService audit.AuditServiceInterface
	log          *logrus.Logger
}

func NewSecretHandler(db *gorm.DB, vaultClient *vault.VaultClient, auditService audit.AuditServiceInterface, log *logrus.Logger) *SecretHandler {
	return &SecretHandler{
		db:           db,
		vaultClient:  vaultClient,
		auditService: auditService,
		log:          log,
	}
}

type CreateSecretRequest struct {
	Name        string            `json:"name" binding:"required"`
	Description string            `json:"description"`
	Type        string            `json:"type" binding:"required"`
	Value       string            `json:"value" binding:"required"`
	Labels      map[string]string `json:"labels"`
	ExpiresAt   *time.Time        `json:"expires_at"`
}

type UpdateSecretRequest struct {
	Description string            `json:"description"`
	Value       string            `json:"value"`
	Labels      map[string]string `json:"labels"`
	ExpiresAt   *time.Time        `json:"expires_at"`
}

type SecretResponse struct {
	ID          uuid.UUID         `json:"id"`
	Name        string            `json:"name"`
	Description string            `json:"description"`
	Type        string            `json:"type"`
	Version     int               `json:"version"`
	CreatedAt   time.Time         `json:"created_at"`
	UpdatedAt   time.Time         `json:"updated_at"`
	ExpiresAt   *time.Time        `json:"expires_at"`
	IsRotated   bool              `json:"is_rotated"`
	Labels      map[string]string `json:"labels"`
}

type SecretWithValueResponse struct {
	SecretResponse
	Value string `json:"value"`
}

func (h *SecretHandler) CreateSecret(c *gin.Context) {
	var req CreateSecretRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	user := c.GetHeader("X-User")
	if user == "" {
		user = "anonymous"
	}

	ctx := context.Background()

	tx := h.db.Begin()
	if tx.Error != nil {
		h.log.Errorf("Failed to start transaction: %v", tx.Error)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create secret"})
		return
	}

	var existingSecret models.Secret
	if err := tx.Where("name = ?", req.Name).First(&existingSecret).Error; err == nil {
		tx.Rollback()
		c.JSON(http.StatusConflict, gin.H{"error": "Secret with this name already exists"})
		return
	}

	var encryptedValue string
	var err error
	if h.vaultClient != nil {
		encryptedValue, err = h.vaultClient.Encrypt(ctx, "secrets-key", []byte(req.Value))
	} else {
		encryptedValue, err = utils.Encrypt(req.Value)
	}
	if err != nil {
		tx.Rollback()
		h.log.Errorf("Failed to encrypt secret value: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to encrypt secret"})
		return
	}

	secret := &models.Secret{
		Name:           req.Name,
		Description:    req.Description,
		Type:           req.Type,
		EncryptedValue: []byte(encryptedValue),
		Version:        1,
		ExpiresAt:      req.ExpiresAt,
		CreatedAt:      time.Now(),
		UpdatedAt:      time.Now(),
	}

	if req.Labels != nil {
		for key, value := range req.Labels {
			secret.Labels = append(secret.Labels, models.Label{Key: key, Value: value})
		}
	}

	if err := tx.Create(secret).Error; err != nil {
		tx.Rollback()
		h.log.Errorf("Failed to create secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create secret"})
		return
	}

	if h.vaultClient != nil {
		vaultData := map[string]interface{}{
			"value":   req.Value,
			"version": 1,
			"type":    req.Type,
		}
		if err := h.vaultClient.StoreSecret(ctx, req.Name, vaultData); err != nil {
			tx.Rollback()
			h.log.Errorf("Failed to store secret in vault: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to store secret"})
			return
		}
	}

	tx.Commit()

	_ = h.auditService.Log(ctx, audit.AuditEntry{
		SecretID:  secret.ID,
		Action:    "CREATE",
		User:      user,
		IPAddress: c.ClientIP(),
		UserAgent: c.Request.UserAgent(),
		Success:   true,
		Message:   "Secret created successfully",
	})

	labels := make(map[string]string)
	for _, label := range secret.Labels {
		labels[label.Key] = label.Value
	}

	c.JSON(http.StatusCreated, SecretResponse{
		ID:          secret.ID,
		Name:        secret.Name,
		Description: secret.Description,
		Type:        secret.Type,
		Version:     secret.Version,
		CreatedAt:   secret.CreatedAt,
		UpdatedAt:   secret.UpdatedAt,
		ExpiresAt:   secret.ExpiresAt,
		IsRotated:   secret.IsRotated,
		Labels:      labels,
	})
}

func (h *SecretHandler) GetSecret(c *gin.Context) {
	idOrName := c.Param("id")
	user := c.GetHeader("X-User")
	if user == "" {
		user = "anonymous"
	}

	ctx := context.Background()

	var secret models.Secret
	var err error

	if uid, parseErr := uuid.Parse(idOrName); parseErr == nil {
		err = h.db.Where("id = ?", uid).Preload("Labels").First(&secret).Error
	} else {
		err = h.db.Where("name = ?", idOrName).Preload("Labels").First(&secret).Error
	}

	if err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "Secret not found"})
			return
		}
		h.log.Errorf("Failed to fetch secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch secret"})
		return
	}

	var value string
	if h.vaultClient != nil {
		vaultData, err := h.vaultClient.GetSecret(ctx, secret.Name)
		if err != nil {
			h.log.Errorf("Failed to get secret from vault: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch secret value"})
			return
		}
		value, _ = vaultData["value"].(string)
	} else {
		decryptedValue, err := utils.Decrypt(string(secret.EncryptedValue))
		if err != nil {
			h.log.Errorf("Failed to decrypt secret: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to decrypt secret"})
			return
		}
		value = decryptedValue
	}

	_ = h.auditService.Log(ctx, audit.AuditEntry{
		SecretID:  secret.ID,
		Action:    "READ",
		User:      user,
		IPAddress: c.ClientIP(),
		UserAgent: c.Request.UserAgent(),
		Success:   true,
		Message:   "Secret accessed",
	})

	labels := make(map[string]string)
	for _, label := range secret.Labels {
		labels[label.Key] = label.Value
	}

	c.JSON(http.StatusOK, SecretWithValueResponse{
		SecretResponse: SecretResponse{
			ID:          secret.ID,
			Name:        secret.Name,
			Description: secret.Description,
			Type:        secret.Type,
			Version:     secret.Version,
			CreatedAt:   secret.CreatedAt,
			UpdatedAt:   secret.UpdatedAt,
			ExpiresAt:   secret.ExpiresAt,
			IsRotated:   secret.IsRotated,
			Labels:      labels,
		},
		Value: value,
	})
}

func (h *SecretHandler) ListSecrets(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	secretType := c.Query("type")

	var secrets []models.Secret
	var total int64

	query := h.db.Model(&models.Secret{}).Preload("Labels")
	if secretType != "" {
		query = query.Where("type = ?", secretType)
	}

	if err := query.Count(&total).Error; err != nil {
		h.log.Errorf("Failed to count secrets: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to list secrets"})
		return
	}

	if err := query.Order("created_at DESC").Limit(limit).Offset(offset).Find(&secrets).Error; err != nil {
		h.log.Errorf("Failed to fetch secrets: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to list secrets"})
		return
	}

	response := make([]SecretResponse, len(secrets))
	for i, secret := range secrets {
		labels := make(map[string]string)
		for _, label := range secret.Labels {
			labels[label.Key] = label.Value
		}
		response[i] = SecretResponse{
			ID:          secret.ID,
			Name:        secret.Name,
			Description: secret.Description,
			Type:        secret.Type,
			Version:     secret.Version,
			CreatedAt:   secret.CreatedAt,
			UpdatedAt:   secret.UpdatedAt,
			ExpiresAt:   secret.ExpiresAt,
			IsRotated:   secret.IsRotated,
			Labels:      labels,
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"secrets": response,
		"total":   total,
		"limit":   limit,
		"offset":  offset,
	})
}

func (h *SecretHandler) UpdateSecret(c *gin.Context) {
	idOrName := c.Param("id")
	user := c.GetHeader("X-User")
	if user == "" {
		user = "anonymous"
	}

	var req UpdateSecretRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()

	tx := h.db.Begin()
	if tx.Error != nil {
		h.log.Errorf("Failed to start transaction: %v", tx.Error)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update secret"})
		return
	}

	var secret models.Secret
	var err error

	if uid, parseErr := uuid.Parse(idOrName); parseErr == nil {
		err = tx.Where("id = ?", uid).Preload("Labels").First(&secret).Error
	} else {
		err = tx.Where("name = ?", idOrName).Preload("Labels").First(&secret).Error
	}

	if err != nil {
		tx.Rollback()
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "Secret not found"})
			return
		}
		h.log.Errorf("Failed to fetch secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch secret"})
		return
	}

	version := &models.SecretVersion{
		SecretID:       secret.ID,
		Version:        secret.Version,
		EncryptedValue: secret.EncryptedValue,
		CreatedAt:      secret.UpdatedAt,
		CreatedBy:      user,
	}
	if err := tx.Create(version).Error; err != nil {
		tx.Rollback()
		h.log.Errorf("Failed to create secret version: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update secret"})
		return
	}

	if req.Description != "" {
		secret.Description = req.Description
	}
	if req.ExpiresAt != nil {
		secret.ExpiresAt = req.ExpiresAt
	}

	var newValue string
	if req.Value != "" {
		var encryptedValue string
		var err error
		if h.vaultClient != nil {
			encryptedValue, err = h.vaultClient.Encrypt(ctx, "secrets-key", []byte(req.Value))
		} else {
			encryptedValue, err = utils.Encrypt(req.Value)
		}
		if err != nil {
			tx.Rollback()
			h.log.Errorf("Failed to encrypt secret value: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to encrypt secret"})
			return
		}
		secret.EncryptedValue = []byte(encryptedValue)
		secret.Version++
		newValue = req.Value
	}

	if req.Labels != nil {
		if err := tx.Model(&secret).Association("Labels").Clear(); err != nil {
			tx.Rollback()
			h.log.Errorf("Failed to clear labels: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update secret"})
			return
		}
		secret.Labels = nil
		for key, value := range req.Labels {
			secret.Labels = append(secret.Labels, models.Label{Key: key, Value: value})
		}
	}

	secret.UpdatedAt = time.Now()

	if err := tx.Save(&secret).Error; err != nil {
		tx.Rollback()
		h.log.Errorf("Failed to update secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update secret"})
		return
	}

	if req.Value != "" && h.vaultClient != nil {
		vaultData := map[string]interface{}{
			"value":   newValue,
			"version": secret.Version,
			"type":    secret.Type,
		}
		if err := h.vaultClient.StoreSecret(ctx, secret.Name, vaultData); err != nil {
			tx.Rollback()
			h.log.Errorf("Failed to store secret in vault: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to store secret"})
			return
		}
	}

	tx.Commit()

	_ = h.auditService.Log(ctx, audit.AuditEntry{
		SecretID:  secret.ID,
		Action:    "UPDATE",
		User:      user,
		IPAddress: c.ClientIP(),
		UserAgent: c.Request.UserAgent(),
		Success:   true,
		Message:   "Secret updated successfully",
	})

	labels := make(map[string]string)
	for _, label := range secret.Labels {
		labels[label.Key] = label.Value
	}

	c.JSON(http.StatusOK, SecretResponse{
		ID:          secret.ID,
		Name:        secret.Name,
		Description: secret.Description,
		Type:        secret.Type,
		Version:     secret.Version,
		CreatedAt:   secret.CreatedAt,
		UpdatedAt:   secret.UpdatedAt,
		ExpiresAt:   secret.ExpiresAt,
		IsRotated:   secret.IsRotated,
		Labels:      labels,
	})
}

func (h *SecretHandler) DeleteSecret(c *gin.Context) {
	idOrName := c.Param("id")
	user := c.GetHeader("X-User")
	if user == "" {
		user = "anonymous"
	}

	ctx := context.Background()

	tx := h.db.Begin()
	if tx.Error != nil {
		h.log.Errorf("Failed to start transaction: %v", tx.Error)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete secret"})
		return
	}

	var secret models.Secret
	var err error

	if uid, parseErr := uuid.Parse(idOrName); parseErr == nil {
		err = tx.Where("id = ?", uid).First(&secret).Error
	} else {
		err = tx.Where("name = ?", idOrName).First(&secret).Error
	}

	if err != nil {
		tx.Rollback()
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "Secret not found"})
			return
		}
		h.log.Errorf("Failed to fetch secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch secret"})
		return
	}

	secretID := secret.ID
	secretName := secret.Name

	if err := tx.Delete(&secret).Error; err != nil {
		tx.Rollback()
		h.log.Errorf("Failed to delete secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete secret"})
		return
	}

	if h.vaultClient != nil {
		if err := h.vaultClient.DeleteSecret(ctx, secretName); err != nil {
			h.log.Warnf("Failed to delete secret from vault: %v", err)
		}
	}

	tx.Commit()

	_ = h.auditService.Log(ctx, audit.AuditEntry{
		SecretID:  secretID,
		Action:    "DELETE",
		User:      user,
		IPAddress: c.ClientIP(),
		UserAgent: c.Request.UserAgent(),
		Success:   true,
		Message:   "Secret deleted successfully",
	})

	c.JSON(http.StatusOK, gin.H{"message": "Secret deleted successfully"})
}

type RotateSecretRequest struct {
	NewValue string `json:"new_value" binding:"required"`
}

func (h *SecretHandler) RotateSecret(c *gin.Context) {
	idOrName := c.Param("id")
	user := c.GetHeader("X-User")
	if user == "" {
		user = "anonymous"
	}

	var req RotateSecretRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()

	tx := h.db.Begin()
	if tx.Error != nil {
		h.log.Errorf("Failed to start transaction: %v", tx.Error)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to rotate secret"})
		return
	}

	var secret models.Secret
	var err error

	if uid, parseErr := uuid.Parse(idOrName); parseErr == nil {
		err = tx.Where("id = ?", uid).First(&secret).Error
	} else {
		err = tx.Where("name = ?", idOrName).First(&secret).Error
	}

	if err != nil {
		tx.Rollback()
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "Secret not found"})
			return
		}
		h.log.Errorf("Failed to fetch secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch secret"})
		return
	}

	version := &models.SecretVersion{
		SecretID:       secret.ID,
		Version:        secret.Version,
		EncryptedValue: secret.EncryptedValue,
		CreatedAt:      secret.UpdatedAt,
		CreatedBy:      user,
	}
	if err := tx.Create(version).Error; err != nil {
		tx.Rollback()
		h.log.Errorf("Failed to create secret version: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to rotate secret"})
		return
	}

	var encryptedValue string
	var err error
	if h.vaultClient != nil {
		encryptedValue, err = h.vaultClient.Encrypt(ctx, "secrets-key", []byte(req.NewValue))
	} else {
		encryptedValue, err = utils.Encrypt(req.NewValue)
	}
	if err != nil {
		tx.Rollback()
		h.log.Errorf("Failed to encrypt secret value: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to encrypt secret"})
		return
	}

	secret.EncryptedValue = []byte(encryptedValue)
	secret.Version++
	now := time.Now()
	secret.LastRotatedAt = &now
	secret.IsRotated = true
	secret.UpdatedAt = now

	if err := tx.Save(&secret).Error; err != nil {
		tx.Rollback()
		h.log.Errorf("Failed to update secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to rotate secret"})
		return
	}

	if h.vaultClient != nil {
		vaultData := map[string]interface{}{
			"value":   req.NewValue,
			"version": secret.Version,
			"type":    secret.Type,
		}
		if err := h.vaultClient.StoreSecret(ctx, secret.Name, vaultData); err != nil {
			tx.Rollback()
			h.log.Errorf("Failed to store secret in vault: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to store secret"})
			return
		}
	}

	tx.Commit()

	_ = h.auditService.Log(ctx, audit.AuditEntry{
		SecretID:  secret.ID,
		Action:    "ROTATE",
		User:      user,
		IPAddress: c.ClientIP(),
		UserAgent: c.Request.UserAgent(),
		Success:   true,
		Message:   "Secret rotated successfully",
	})

	c.JSON(http.StatusOK, gin.H{
		"message":        "Secret rotated successfully",
		"new_version":    secret.Version,
		"rotated_at":     secret.LastRotatedAt,
	})
}

type AuditHandler struct {
	auditService audit.AuditServiceInterface
	log          *logrus.Logger
}

func NewAuditHandler(auditService audit.AuditServiceInterface, log *logrus.Logger) *AuditHandler {
	return &AuditHandler{
		auditService: auditService,
		log:          log,
	}
}

func (h *AuditHandler) GetAuditLogs(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	user := c.Query("user")
	secretID := c.Query("secret_id")

	ctx := context.Background()

	var logs []models.AuditLog
	var total int64
	var err error

	if secretID != "" {
		if uid, parseErr := uuid.Parse(secretID); parseErr == nil {
			logs, total, err = h.auditService.GetLogsBySecret(ctx, uid, limit, offset)
		}
	} else if user != "" {
		logs, total, err = h.auditService.GetLogsByUser(ctx, user, limit, offset)
	} else {
		logs, total, err = h.auditService.GetAllLogs(ctx, limit, offset)
	}

	if err != nil {
		h.log.Errorf("Failed to fetch audit logs: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch audit logs"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"logs":   logs,
		"total":  total,
		"limit":  limit,
		"offset": offset,
	})
}

func (h *AuditHandler) GetAuditStats(c *gin.Context) {
	ctx := context.Background()

	stats, err := h.auditService.GetActionStats(ctx)
	if err != nil {
		h.log.Errorf("Failed to get audit stats: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get audit stats"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"stats": stats})
}

type HealthHandler struct {
	db           *gorm.DB
	vaultClient  *vault.VaultClient
	auditService audit.AuditServiceInterface
	log          *logrus.Logger
}

func NewHealthHandler(db *gorm.DB, vaultClient *vault.VaultClient, auditService audit.AuditServiceInterface, log *logrus.Logger) *HealthHandler {
	return &HealthHandler{
		db:           db,
		vaultClient:  vaultClient,
		auditService: auditService,
		log:          log,
	}
}

func (h *HealthHandler) HealthCheck(c *gin.Context) {
	ctx := context.Background()

	status := "healthy"
	services := make(map[string]string)

	dbSQL, err := h.db.DB()
	if err != nil || dbSQL.PingContext(ctx) != nil {
		status = "unhealthy"
		services["database"] = "unhealthy"
	} else {
		services["database"] = "healthy"
	}

	if h.vaultClient != nil {
		if err := h.vaultClient.HealthCheck(ctx); err != nil {
			status = "unhealthy"
			services["vault"] = "unhealthy"
		} else {
			services["vault"] = "healthy"
		}
	} else {
		services["vault"] = "not_configured"
	}

	services["api"] = "healthy"

	response := gin.H{
		"status":   status,
		"services": services,
		"time":     time.Now(),
	}

	if asyncSvc, ok := h.auditService.(*audit.AuditServiceWithAsync); ok {
		if metrics := asyncSvc.GetAsyncMetrics(); metrics != nil {
			response["audit_async_metrics"] = gin.H{
				"total_received":   metrics.TotalReceived,
				"total_written":    metrics.TotalWritten,
				"total_dropped":    metrics.TotalDropped,
				"current_queue_len": metrics.CurrentQueueLen,
			}
		}
	}

	c.JSON(http.StatusOK, response)
}

type VersionHandler struct {
	versionService *version.VersionService
	log            *logrus.Logger
}

func NewVersionHandler(versionService *version.VersionService, log *logrus.Logger) *VersionHandler {
	return &VersionHandler{
		versionService: versionService,
		log:            log,
	}
}

func (h *VersionHandler) GetSecretVersions(c *gin.Context) {
	secretIDStr := c.Param("id")
	secretID, err := uuid.Parse(secretIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid secret ID"})
		return
	}

	ctx := context.Background()
	versions, err := h.versionService.GetSecretVersions(ctx, secretID)
	if err != nil {
		h.log.Errorf("Failed to get secret versions: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get versions"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"versions": versions})
}

type DecryptWithVersionRequest struct {
	Version       int    `json:"version" binding:"required"`
	EncryptedData string `json:"encrypted_data" binding:"required"`
}

func (h *VersionHandler) DecryptWithVersion(c *gin.Context) {
	secretIDStr := c.Param("id")
	secretID, err := uuid.Parse(secretIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid secret ID"})
		return
	}

	var req DecryptWithVersionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()
	result, err := h.versionService.DecryptWithVersion(ctx, secretID, req.Version, req.EncryptedData)
	if err != nil {
		h.log.Errorf("Failed to decrypt with version: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

type CreateDataRecordRequest struct {
	DataReference string `json:"data_reference" binding:"required"`
	Description   string `json:"description"`
}

func (h *VersionHandler) CreateDataRecord(c *gin.Context) {
	secretIDStr := c.Param("id")
	secretID, err := uuid.Parse(secretIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid secret ID"})
		return
	}

	var req CreateDataRecordRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	user := c.GetHeader("X-User")
	if user == "" {
		user = "anonymous"
	}

	ctx := context.Background()
	record, err := h.versionService.CreateDataRecord(ctx, secretID, req.DataReference, req.Description, user)
	if err != nil {
		h.log.Errorf("Failed to create data record: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create data record"})
		return
	}

	c.JSON(http.StatusCreated, record)
}

func (h *VersionHandler) DecryptHistoricalData(c *gin.Context) {
	recordIDStr := c.Param("record_id")
	recordID, err := uuid.Parse(recordIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid record ID"})
		return
	}

	ctx := context.Background()
	result, err := h.versionService.DecryptHistoricalData(ctx, recordID)
	if err != nil {
		h.log.Errorf("Failed to decrypt historical data: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

type RollbackRequest struct {
	TargetVersion int `json:"target_version" binding:"required"`
}

func (h *VersionHandler) RollbackToVersion(c *gin.Context) {
	secretIDStr := c.Param("id")
	secretID, err := uuid.Parse(secretIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid secret ID"})
		return
	}

	var req RollbackRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	user := c.GetHeader("X-User")
	if user == "" {
		user = "anonymous"
	}

	ctx := context.Background()
	err = h.versionService.RollbackToVersion(ctx, secretID, req.TargetVersion, user)
	if err != nil {
		h.log.Errorf("Failed to rollback: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Rollback successful"})
}

func (h *VersionHandler) CompareVersions(c *gin.Context) {
	secretIDStr := c.Param("id")
	secretID, err := uuid.Parse(secretIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid secret ID"})
		return
	}

	v1, _ := strconv.Atoi(c.Query("v1"))
	v2, _ := strconv.Atoi(c.Query("v2"))

	if v1 == 0 || v2 == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Both versions (v1, v2) are required"})
		return
	}

	ctx := context.Background()
	diff, err := h.versionService.CompareVersions(ctx, secretID, v1, v2)
	if err != nil {
		h.log.Errorf("Failed to compare versions: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, diff)
}

type ComplianceHandler struct {
	complianceService *compliance.ComplianceService
	log               *logrus.Logger
}

func NewComplianceHandler(complianceService *compliance.ComplianceService, log *logrus.Logger) *ComplianceHandler {
	return &ComplianceHandler{
		complianceService: complianceService,
		log:               log,
	}
}

func (h *ComplianceHandler) CheckPasswordStrength(c *gin.Context) {
	var req struct {
		Password string `json:"password" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	strength := h.complianceService.CheckPasswordStrength(req.Password)
	c.JSON(http.StatusOK, strength)
}

func (h *ComplianceHandler) CheckSecret(c *gin.Context) {
	secretID := c.Param("id")

	ctx := context.Background()

	config := compliance.DefaultConfig()

	result, err := h.complianceService.CheckSecret(ctx, secretID, "dummy_value", config)
	if err != nil {
		h.log.Errorf("Failed to check secret: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to check secret"})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *ComplianceHandler) RunFullScan(c *gin.Context) {
	ctx := context.Background()
	config := compliance.DefaultConfig()

	report, err := h.complianceService.RunFullScan(ctx, config)
	if err != nil {
		h.log.Errorf("Failed to run compliance scan: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to run scan"})
		return
	}

	c.JSON(http.StatusOK, report)
}

func (h *ComplianceHandler) GetCheckHistory(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	secretID := c.Query("secret_id")

	ctx := context.Background()
	checks, total, err := h.complianceService.GetCheckHistory(ctx, secretID, limit, offset)
	if err != nil {
		h.log.Errorf("Failed to get check history: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get history"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"checks": checks,
		"total":  total,
		"limit":  limit,
		"offset": offset,
	})
}

type RecoveryHandler struct {
	recoveryService *recovery.RecoveryService
	log             *logrus.Logger
}

func NewRecoveryHandler(recoveryService *recovery.RecoveryService, log *logrus.Logger) *RecoveryHandler {
	return &RecoveryHandler{
		recoveryService: recoveryService,
		log:             log,
	}
}

func (h *RecoveryHandler) GetAvailableExercises(c *gin.Context) {
	exercises := h.recoveryService.GetAvailableExercises()
	c.JSON(http.StatusOK, gin.H{"exercises": exercises})
}

type StartExerciseRequest struct {
	ExerciseType string `json:"exercise_type" binding:"required"`
}

func (h *RecoveryHandler) StartExercise(c *gin.Context) {
	var req StartExerciseRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	user := c.GetHeader("X-User")
	if user == "" {
		user = "anonymous"
	}

	ctx := context.Background()
	report, err := h.recoveryService.StartExercise(ctx, recovery.ExerciseType(req.ExerciseType), user)
	if err != nil {
		h.log.Errorf("Failed to start exercise: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, report)
}

func (h *RecoveryHandler) GetExerciseHistory(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))

	ctx := context.Background()
	exercises, total, err := h.recoveryService.GetExerciseHistory(ctx, limit, offset)
	if err != nil {
		h.log.Errorf("Failed to get exercise history: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get history"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"exercises": exercises,
		"total":     total,
		"limit":     limit,
		"offset":    offset,
	})
}

func (h *RecoveryHandler) GetExerciseDetail(c *gin.Context) {
	exerciseID := c.Param("id")

	ctx := context.Background()
	report, err := h.recoveryService.GetExerciseDetail(ctx, exerciseID)
	if err != nil {
		h.log.Errorf("Failed to get exercise detail: %v", err)
		c.JSON(http.StatusNotFound, gin.H{"error": "Exercise not found"})
		return
	}

	c.JSON(http.StatusOK, report)
}

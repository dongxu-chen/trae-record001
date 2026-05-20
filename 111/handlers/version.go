package handlers

import (
	"net/http"

	"cloud-storage-gateway/database"
	"cloud-storage-gateway/seaweedfs"

	"github.com/gin-gonic/gin"
)

type RestoreVersionRequest struct {
	FileID    string `json:"file_id" binding:"required"`
	VersionID string `json:"version_id" binding:"required"`
}

type SetExpirationRequest struct {
	FileID string `json:"file_id" binding:"required"`
	Days   int    `json:"days" binding:"required,min=1"`
}

type SetGlobalExpirationRequest struct {
	Days int `json:"days" binding:"required,min=1"`
}

func GetObjectVersions(c *gin.Context) {
	fileID := c.Param("file_id")

	metadata, err := database.GetFileMetadata(fileID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "File not found"})
		return
	}

	versions, err := seaweedfs.SWClient.ListObjectVersions(c.Request.Context(), metadata.ObjectPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to list object versions"})
		return
	}

	type VersionInfo struct {
		VersionID   string `json:"version_id"`
		IsLatest    bool   `json:"is_latest"`
		Size        int64  `json:"size"`
		ETag        string `json:"etag"`
		LastModified string `json:"last_modified"`
		IsDeleteMarker bool `json:"is_delete_marker"`
	}

	result := make([]VersionInfo, 0, len(versions))
	for _, v := range versions {
		result = append(result, VersionInfo{
			VersionID:    v.VersionID,
			IsLatest:     v.IsLatest,
			Size:         v.Size,
			ETag:         v.ETag,
			LastModified: v.LastModified.String(),
			IsDeleteMarker: v.IsDeleteMarker,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"file_id":  fileID,
		"versions": result,
	})
}

func RestoreObjectVersion(c *gin.Context) {
	var req RestoreVersionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	metadata, err := database.GetFileMetadata(req.FileID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "File not found"})
		return
	}

	if err := seaweedfs.SWClient.RestoreObjectVersion(c.Request.Context(), metadata.ObjectPath, req.VersionID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to restore version"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":    "Version restored successfully",
		"file_id":    req.FileID,
		"version_id": req.VersionID,
	})
}

func DeleteObjectVersion(c *gin.Context) {
	fileID := c.Param("file_id")
	versionID := c.Query("version_id")

	if versionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "version_id query parameter is required"})
		return
	}

	metadata, err := database.GetFileMetadata(fileID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "File not found"})
		return
	}

	if err := seaweedfs.SWClient.DeleteObjectVersion(c.Request.Context(), metadata.ObjectPath, versionID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete version"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":    "Version deleted successfully",
		"file_id":    fileID,
		"version_id": versionID,
	})
}

func GetVersioningStatus(c *gin.Context) {
	enabled, err := seaweedfs.SWClient.GetVersioningStatus(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get versioning status"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"enabled": enabled,
	})
}

func SetObjectExpiration(c *gin.Context) {
	var req SetExpirationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	metadata, err := database.GetFileMetadata(req.FileID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "File not found"})
		return
	}

	if err := seaweedfs.SWClient.SetObjectExpiration(c.Request.Context(), metadata.ObjectPath, req.Days); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to set expiration"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Expiration set successfully",
		"file_id": req.FileID,
		"days":    req.Days,
	})
}

func SetGlobalExpiration(c *gin.Context) {
	var req SetGlobalExpirationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := seaweedfs.SWClient.SetGlobalExpiration(c.Request.Context(), req.Days); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to set global expiration"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Global expiration set successfully",
		"days":    req.Days,
	})
}

func SetNoncurrentVersionExpiration(c *gin.Context) {
	var req SetGlobalExpirationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := seaweedfs.SWClient.SetNoncurrentVersionExpiration(c.Request.Context(), req.Days); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to set noncurrent version expiration"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Noncurrent version expiration set successfully",
		"days":    req.Days,
	})
}

func GetLifecycleConfig(c *gin.Context) {
	config, err := seaweedfs.SWClient.GetLifecycle(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get lifecycle configuration"})
		return
	}

	type RuleInfo struct {
		ID     string `json:"id"`
		Status string `json:"status"`
		Prefix string `json:"prefix"`
		ExpirationDays int `json:"expiration_days,omitempty"`
		NoncurrentDays int `json:"noncurrent_days,omitempty"`
	}

	rules := make([]RuleInfo, 0, len(config.Rules))
	for _, rule := range config.Rules {
		info := RuleInfo{
			ID:     rule.ID,
			Status: rule.Status,
			Prefix: rule.Filter.Prefix,
		}
		if rule.Expiration.Days > 0 {
			info.ExpirationDays = int(rule.Expiration.Days)
		}
		if rule.NoncurrentVersionExpiration.NoncurrentDays > 0 {
			info.NoncurrentDays = int(rule.NoncurrentVersionExpiration.NoncurrentDays)
		}
		rules = append(rules, info)
	}

	c.JSON(http.StatusOK, gin.H{"rules": rules})
}

func RemoveLifecycleRule(c *gin.Context) {
	ruleID := c.Param("rule_id")

	if err := seaweedfs.SWClient.RemoveLifecycleRule(c.Request.Context(), ruleID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to remove lifecycle rule"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Lifecycle rule removed successfully",
		"rule_id": ruleID,
	})
}

func GetMergeStats(c *gin.Context) {
	stats := seaweedfs.GetMergeStats()
	c.JSON(http.StatusOK, stats)
}

func TriggerMerge(c *gin.Context) {
	seaweedfs.SmallFileMgr.Flush()
	c.JSON(http.StatusOK, gin.H{"message": "Merge triggered"})
}

func GetReplicationPeers(c *gin.Context) {
	peers := seaweedfs.ReplicationMgr.GetAllPeers()
	c.JSON(http.StatusOK, gin.H{"peers": peers})
}

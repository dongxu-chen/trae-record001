package handlers

import (
	"net/http"

	"cloud-storage-gateway/kms"

	"github.com/gin-gonic/gin"
)

type CreateKeyRequest struct {
	KeyID       string `json:"key_id" binding:"required"`
	Description string `json:"description"`
}

type ImportKeyRequest struct {
	KeyID       string `json:"key_id" binding:"required"`
	KeyMaterial string `json:"key_material" binding:"required"`
	Description string `json:"description"`
}

type GenerateDataKeyRequest struct {
	KeyID string `json:"key_id" binding:"required"`
}

func CreateKey(c *gin.Context) {
	var req CreateKeyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	keyMeta, err := kms.CreateKey(req.KeyID, req.Description)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":  "Key created successfully",
		"key_meta": keyMeta,
	})
}

func ListKeys(c *gin.Context) {
	keys := kms.ListKeys()
	c.JSON(http.StatusOK, gin.H{"keys": keys})
}

func GetKeyMetadata(c *gin.Context) {
	keyID := c.Param("key_id")

	meta, err := kms.GetKeyMetadata(keyID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Key not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"key_meta": meta})
}

func EnableKey(c *gin.Context) {
	keyID := c.Param("key_id")

	if err := kms.EnableKey(keyID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Key enabled successfully"})
}

func DisableKey(c *gin.Context) {
	keyID := c.Param("key_id")

	if err := kms.DisableKey(keyID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Key disabled successfully"})
}

func RotateKey(c *gin.Context) {
	keyID := c.Param("key_id")

	meta, err := kms.RotateKey(keyID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":  "Key rotated successfully",
		"key_meta": meta,
	})
}

func ExportKey(c *gin.Context) {
	keyID := c.Param("key_id")

	keyMaterial, err := kms.ExportKey(keyID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"key_id":       keyID,
		"key_material": keyMaterial,
	})
}

func ImportKey(c *gin.Context) {
	var req ImportKeyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	meta, err := kms.ImportKey(req.KeyID, req.KeyMaterial, req.Description)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":  "Key imported successfully",
		"key_meta": meta,
	})
}

func GenerateDataKey(c *gin.Context) {
	var req GenerateDataKeyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	plaintext, ciphertext, err := kms.GenerateDataKey(req.KeyID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"key_id":       req.KeyID,
		"plaintext":    plaintext,
		"ciphertext":   ciphertext,
	})
}

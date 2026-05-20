package handlers

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"cloud-storage-gateway/config"
	"cloud-storage-gateway/database"
	"cloud-storage-gateway/models"
	"cloud-storage-gateway/redis"
	"cloud-storage-gateway/seaweedfs"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/minio/minio-go/v7"
)

type InitUploadRequest struct {
	FileName      string `json:"file_name" binding:"required"`
	FileSize      int64  `json:"file_size" binding:"required"`
	FileType      string `json:"file_type"`
	MD5Hash       string `json:"md5_hash"`
	EncryptionKeyID string `json:"encryption_key_id"`
}

type InitUploadResponse struct {
	FileID      string `json:"file_id"`
	TotalChunks int    `json:"total_chunks"`
	ChunkSize   int    `json:"chunk_size"`
	IsDuplicate bool   `json:"is_duplicate"`
}

type UploadChunkRequest struct {
	FileID      string `form:"file_id" binding:"required"`
	ChunkNumber int    `form:"chunk_number" binding:"required"`
}

type CompleteUploadRequest struct {
	FileID  string `json:"file_id" binding:"required"`
	MD5Hash string `json:"md5_hash"`
}

func InitUpload(c *gin.Context) {
	var req InitUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.FileSize > config.MaxFileSize {
		c.JSON(http.StatusBadRequest, gin.H{"error": "File size exceeds maximum limit of 5GB"})
		return
	}

	if req.MD5Hash != "" {
		var existingFile models.FileMetadata
		if err := database.DB.Where("md5_hash = ? AND status = ?", req.MD5Hash, models.UploadStatusComplete).First(&existingFile).Error; err == nil {
			existingFile.RefCount++
			database.DB.Save(&existingFile)
			c.JSON(http.StatusOK, InitUploadResponse{
				FileID:      existingFile.FileID,
				TotalChunks: existingFile.TotalChunks,
				ChunkSize:   config.ChunkSize,
				IsDuplicate: true,
			})
			return
		}

		cachedFileID, err := redis.GetFileIDByMD5(c.Request.Context(), req.MD5Hash)
		if err == nil && cachedFileID != "" {
			var existingFile models.FileMetadata
			if err := database.DB.Where("file_id = ?", cachedFileID).First(&existingFile).Error; err == nil {
				if existingFile.Status == models.UploadStatusComplete {
					existingFile.RefCount++
					database.DB.Save(&existingFile)
					c.JSON(http.StatusOK, InitUploadResponse{
						FileID:      existingFile.FileID,
						TotalChunks: existingFile.TotalChunks,
						ChunkSize:   config.ChunkSize,
						IsDuplicate: true,
					})
					return
				}
			}
		}
	}

	totalChunks := int((req.FileSize + int64(config.ChunkSize) - 1) / int64(config.ChunkSize))
	fileID := uuid.New().String()

	isEncrypted := req.EncryptionKeyID != ""
	metadata := &models.FileMetadata{
		FileID:          fileID,
		FileName:        req.FileName,
		FileSize:        req.FileSize,
		FileType:        req.FileType,
		TotalChunks:     totalChunks,
		Status:          models.UploadStatusInit,
		MD5Hash:         req.MD5Hash,
		EncryptionKeyID: req.EncryptionKeyID,
		IsEncrypted:     isEncrypted,
		RefCount:        1,
	}

	if err := database.CreateFileMetadata(metadata); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create file metadata"})
		return
	}

	session := &redis.UploadSession{
		FileID:      fileID,
		FileName:    req.FileName,
		FileSize:    req.FileSize,
		FileType:    req.FileType,
		TotalChunks: totalChunks,
		ChunkSize:   config.ChunkSize,
		Status:      models.UploadStatusInit,
		CreatedAt:   time.Now(),
	}

	if err := redis.SaveUploadSession(c.Request.Context(), session); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save upload session"})
		return
	}

	if req.MD5Hash != "" {
		redis.SaveFileMD5(c.Request.Context(), req.MD5Hash, fileID)
	}

	c.JSON(http.StatusOK, InitUploadResponse{
		FileID:      fileID,
		TotalChunks: totalChunks,
		ChunkSize:   config.ChunkSize,
		IsDuplicate: false,
	})
}

func UploadChunk(c *gin.Context) {
	fileID := c.PostForm("file_id")
	chunkNumberStr := c.PostForm("chunk_number")

	if fileID == "" || chunkNumberStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file_id and chunk_number are required"})
		return
	}

	chunkNumber, err := parseChunkNumber(chunkNumberStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid chunk_number"})
		return
	}

	session, err := redis.GetUploadSession(c.Request.Context(), fileID)
	if err != nil {
		metadata, err := database.GetFileMetadata(fileID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "File upload session not found"})
			return
		}
		session = &redis.UploadSession{
			FileID:      fileID,
			FileName:    metadata.FileName,
			FileSize:    metadata.FileSize,
			FileType:    metadata.FileType,
			TotalChunks: metadata.TotalChunks,
			ChunkSize:   config.ChunkSize,
			Status:      metadata.Status,
			CreatedAt:   metadata.CreatedAt,
		}
		redis.SaveUploadSession(c.Request.Context(), session)
	}

	if chunkNumber < 1 || chunkNumber > session.TotalChunks {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid chunk number"})
		return
	}

	uploaded, err := redis.IsChunkUploaded(c.Request.Context(), fileID, chunkNumber)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to check chunk status"})
		return
	}
	if uploaded {
		c.JSON(http.StatusOK, gin.H{"message": "Chunk already uploaded", "chunk_number": chunkNumber})
		return
	}

	expectedChunk := getNextExpectedChunk(c.Request.Context(), fileID, session.TotalChunks)
	if chunkNumber != expectedChunk {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":           "Chunks must be uploaded in order",
			"expected_chunk":  expectedChunk,
			"received_chunk":  chunkNumber,
		})
		return
	}

	fileHeader, err := c.FormFile("chunk")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Chunk file is required"})
		return
	}

	file, err := fileHeader.Open()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to open chunk file"})
		return
	}
	defer file.Close()

	chunkPath := fmt.Sprintf("chunks/%s/%d", fileID, chunkNumber)
	if err := seaweedfs.SWClient.UploadChunk(c.Request.Context(), chunkPath, file, fileHeader.Size); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to upload chunk"})
		return
	}

	chunkInfo := &redis.ChunkInfo{
		ChunkNumber: chunkNumber,
		ChunkSize:   fileHeader.Size,
		ChunkPath:   chunkPath,
		UploadedAt:  time.Now(),
	}

	if err := redis.SaveChunkInfo(c.Request.Context(), fileID, chunkInfo); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to record chunk"})
		return
	}

	if session.Status == models.UploadStatusInit {
		session.Status = models.UploadStatusUploading
		redis.SaveUploadSession(c.Request.Context(), session)

		metadata, _ := database.GetFileMetadata(fileID)
		if metadata != nil {
			metadata.Status = models.UploadStatusUploading
			database.UpdateFileMetadata(metadata)
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"message":       "Chunk uploaded successfully",
		"chunk_number":  chunkNumber,
		"file_id":       fileID,
		"next_expected": getNextExpectedChunk(c.Request.Context(), fileID, session.TotalChunks),
	})
}

func getNextExpectedChunk(ctx context.Context, fileID string, totalChunks int) int {
	for i := 1; i <= totalChunks; i++ {
		uploaded, _ := redis.IsChunkUploaded(ctx, fileID, i)
		if !uploaded {
			return i
		}
	}
	return totalChunks + 1
}

func parseChunkNumber(s string) (int, error) {
	var result int
	_, err := fmt.Sscanf(s, "%d", &result)
	return result, err
}

func GetUploadStatus(c *gin.Context) {
	fileID := c.Param("file_id")

	session, err := redis.GetUploadSession(c.Request.Context(), fileID)
	if err != nil {
		metadata, err := database.GetFileMetadata(fileID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "File upload session not found"})
			return
		}

		chunks, _ := database.GetUploadedChunks(fileID)
		uploadedChunkNumbers := make([]int, 0, len(chunks))
		for _, chunk := range chunks {
			uploadedChunkNumbers = append(uploadedChunkNumbers, chunk.ChunkNumber)
		}

		c.JSON(http.StatusOK, gin.H{
			"file_id":             fileID,
			"file_name":           metadata.FileName,
			"status":              metadata.Status,
			"total_chunks":        metadata.TotalChunks,
			"uploaded_chunks":     len(uploadedChunkNumbers),
			"uploaded_chunk_list": uploadedChunkNumbers,
			"next_expected":       getNextExpectedChunkFromList(uploadedChunkNumbers, metadata.TotalChunks),
		})
		return
	}

	uploadedChunkNumbers, _ := redis.GetUploadedChunkNumbers(c.Request.Context(), fileID, session.TotalChunks)

	c.JSON(http.StatusOK, gin.H{
		"file_id":             fileID,
		"file_name":           session.FileName,
		"status":              session.Status,
		"total_chunks":        session.TotalChunks,
		"uploaded_chunks":     len(uploadedChunkNumbers),
		"uploaded_chunk_list": uploadedChunkNumbers,
		"next_expected":       getNextExpectedChunkFromList(uploadedChunkNumbers, session.TotalChunks),
	})
}

func getNextExpectedChunkFromList(uploaded []int, total int) int {
	uploadedMap := make(map[int]bool)
	for _, num := range uploaded {
		uploadedMap[num] = true
	}
	for i := 1; i <= total; i++ {
		if !uploadedMap[i] {
			return i
		}
	}
	return total + 1
}

func CompleteUpload(c *gin.Context) {
	var req CompleteUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	metadata, err := database.GetFileMetadata(req.FileID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "File upload session not found"})
		return
	}

	if metadata.Status == models.UploadStatusComplete {
		c.JSON(http.StatusOK, gin.H{
			"message":     "File already uploaded",
			"file_id":     req.FileID,
			"object_path": metadata.ObjectPath,
		})
		return
	}

	session, err := redis.GetUploadSession(c.Request.Context(), req.FileID)
	if err != nil {
		session = &redis.UploadSession{
			FileID:      req.FileID,
			TotalChunks: metadata.TotalChunks,
		}
	}

	chunks, err := redis.GetUploadedChunks(c.Request.Context(), req.FileID, session.TotalChunks)
	if err != nil || len(chunks) == 0 {
		dbChunks, _ := database.GetUploadedChunks(req.FileID)
		if len(dbChunks) != metadata.TotalChunks {
			c.JSON(http.StatusBadRequest, gin.H{
				"error":           "Not all chunks uploaded",
				"uploaded_chunks": len(dbChunks),
				"total_chunks":    metadata.TotalChunks,
			})
			return
		}
		chunks = make([]redis.ChunkInfo, len(dbChunks))
		for i, dbChunk := range dbChunks {
			chunks[i] = redis.ChunkInfo{
				ChunkNumber: dbChunk.ChunkNumber,
				ChunkSize:   dbChunk.ChunkSize,
				ChunkPath:   dbChunk.ChunkPath,
				UploadedAt:  dbChunk.UploadedAt,
			}
		}
	}

	if len(chunks) != metadata.TotalChunks {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":           "Not all chunks uploaded",
			"uploaded_chunks": len(chunks),
			"total_chunks":    metadata.TotalChunks,
		})
		return
	}

	sort.Slice(chunks, func(i, j int) bool {
		return chunks[i].ChunkNumber < chunks[j].ChunkNumber
	})

	sources := make([]minio.CopySrcOptions, len(chunks))
	for i, chunk := range chunks {
		sources[i] = minio.CopySrcOptions{
			Bucket: config.SeaweedFSBucketName,
			Object: chunk.ChunkPath,
		}
	}

	objectPath := fmt.Sprintf("files/%s%s", req.FileID, filepath.Ext(metadata.FileName))
	if metadata.IsEncrypted && metadata.EncryptionKeyID != "" {
		if err := seaweedfs.SWClient.ComposeObjectWithEncryption(c.Request.Context(), objectPath, sources, metadata.EncryptionKeyID); err != nil {
			metadata.Status = models.UploadStatusFailed
			database.UpdateFileMetadata(metadata)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to compose encrypted file"})
			return
		}
	} else {
		if err := seaweedfs.SWClient.ComposeObject(c.Request.Context(), objectPath, sources); err != nil {
			metadata.Status = models.UploadStatusFailed
			database.UpdateFileMetadata(metadata)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to compose file"})
			return
		}
	}

	chunkPaths := make([]string, len(chunks))
	for i, chunk := range chunks {
		chunkPaths[i] = chunk.ChunkPath
	}
	if err := seaweedfs.SWClient.DeleteObjects(c.Request.Context(), chunkPaths); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to clean up chunks"})
		return
	}

	metadata.ObjectPath = objectPath
	metadata.Status = models.UploadStatusComplete
	if req.MD5Hash != "" {
		metadata.MD5Hash = req.MD5Hash
	}

	if metadata.MD5Hash != "" {
		var existingFile models.FileMetadata
		if err := database.DB.Where("md5_hash = ? AND status = ? AND file_id != ?",
			metadata.MD5Hash, models.UploadStatusComplete, req.FileID).First(&existingFile).Error; err == nil {
			seaweedfs.SWClient.DeleteObject(c.Request.Context(), objectPath)
			redis.DeleteChunkInfos(c.Request.Context(), req.FileID, metadata.TotalChunks)
			redis.DeleteUploadSession(c.Request.Context(), req.FileID)
			database.DeleteFileMetadata(req.FileID)

			existingFile.RefCount++
			database.DB.Save(&existingFile)

			c.JSON(http.StatusOK, gin.H{
				"message":       "File deduplicated",
				"file_id":       existingFile.FileID,
				"object_path":   existingFile.ObjectPath,
				"is_duplicate":  true,
			})
			return
		}
	}

	if config.EnableSmallFileMerge && seaweedfs.IsSmallFile(metadata.FileSize) {
		seaweedfs.SmallFileMgr.AddSmallFile(metadata.FileID, metadata.FileName, metadata.FileSize, nil)
	}

	if err := database.UpdateFileMetadata(metadata); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update file metadata"})
		return
	}

	redis.DeleteChunkInfos(c.Request.Context(), req.FileID, metadata.TotalChunks)
	redis.DeleteUploadSession(c.Request.Context(), req.FileID)
	database.DeleteChunkRecords(req.FileID)

	if metadata.MD5Hash != "" {
		redis.SaveFileMD5(c.Request.Context(), metadata.MD5Hash, req.FileID)
	}

	c.JSON(http.StatusOK, gin.H{
		"message":     "File upload completed successfully",
		"file_id":     req.FileID,
		"object_path": objectPath,
	})
}

func UploadChunkMD5(c *gin.Context) {
	fileID := c.PostForm("file_id")
	chunkNumberStr := c.PostForm("chunk_number")
	chunkMD5 := c.PostForm("chunk_md5")

	if fileID == "" || chunkNumberStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file_id and chunk_number are required"})
		return
	}

	chunkNumber, err := parseChunkNumber(chunkNumberStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid chunk_number"})
		return
	}

	session, err := redis.GetUploadSession(c.Request.Context(), fileID)
	if err != nil {
		metadata, err := database.GetFileMetadata(fileID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "File upload session not found"})
			return
		}
		session = &redis.UploadSession{
			FileID:      fileID,
			TotalChunks: metadata.TotalChunks,
		}
	}

	if chunkNumber < 1 || chunkNumber > session.TotalChunks {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid chunk number"})
		return
	}

	uploaded, err := redis.IsChunkUploaded(c.Request.Context(), fileID, chunkNumber)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to check chunk status"})
		return
	}
	if uploaded {
		c.JSON(http.StatusOK, gin.H{"message": "Chunk already uploaded", "chunk_number": chunkNumber})
		return
	}

	expectedChunk := getNextExpectedChunk(c.Request.Context(), fileID, session.TotalChunks)
	if chunkNumber != expectedChunk {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":          "Chunks must be uploaded in order",
			"expected_chunk": expectedChunk,
			"received_chunk": chunkNumber,
		})
		return
	}

	fileHeader, err := c.FormFile("chunk")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Chunk file is required"})
		return
	}

	file, err := fileHeader.Open()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to open chunk file"})
		return
	}
	defer file.Close()

	var fileContent []byte
	if chunkMD5 != "" {
		fileContent, err = io.ReadAll(file)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read chunk file"})
			return
		}
		hash := md5.Sum(fileContent)
		calculatedMD5 := hex.EncodeToString(hash[:])
		if calculatedMD5 != chunkMD5 {
			c.JSON(http.StatusBadRequest, gin.H{
				"error":         "Chunk MD5 mismatch",
				"expected_md5":  chunkMD5,
				"calculated_md5": calculatedMD5,
			})
			return
		}
	}

	chunkPath := fmt.Sprintf("chunks/%s/%d", fileID, chunkNumber)
	if fileContent != nil {
		reader := strings.NewReader(string(fileContent))
		if err := seaweedfs.SWClient.UploadChunk(c.Request.Context(), chunkPath, reader, fileHeader.Size); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to upload chunk"})
			return
		}
	} else {
		if err := seaweedfs.SWClient.UploadChunk(c.Request.Context(), chunkPath, file, fileHeader.Size); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to upload chunk"})
			return
		}
	}

	chunkInfo := &redis.ChunkInfo{
		ChunkNumber: chunkNumber,
		ChunkSize:   fileHeader.Size,
		ChunkPath:   chunkPath,
		UploadedAt:  time.Now(),
	}

	if err := redis.SaveChunkInfo(c.Request.Context(), fileID, chunkInfo); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to record chunk"})
		return
	}

	if session.Status == models.UploadStatusInit {
		session.Status = models.UploadStatusUploading
		redis.SaveUploadSession(c.Request.Context(), session)

		metadata, _ := database.GetFileMetadata(fileID)
		if metadata != nil {
			metadata.Status = models.UploadStatusUploading
			database.UpdateFileMetadata(metadata)
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"message":       "Chunk uploaded successfully",
		"chunk_number":  chunkNumber,
		"file_id":       fileID,
		"next_expected": getNextExpectedChunk(c.Request.Context(), fileID, session.TotalChunks),
	})
}

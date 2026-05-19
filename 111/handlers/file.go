package handlers

import (
	"bytes"
	"context"
	"io"
	"net/http"
	"strconv"
	"strings"

	"cloud-storage-gateway/config"
	"cloud-storage-gateway/database"
	"cloud-storage-gateway/models"
	"cloud-storage-gateway/redis"
	"cloud-storage-gateway/seaweedfs"

	"github.com/gin-gonic/gin"
)

type Range struct {
	Start int64
	End   int64
}

func parseRangeHeader(rangeHeader string, fileSize int64) ([]Range, error) {
	if rangeHeader == "" {
		return nil, nil
	}

	parts := strings.SplitN(rangeHeader, "=", 2)
	if len(parts) != 2 || parts[0] != "bytes" {
		return nil, nil
	}

	rangeSpecs := strings.Split(parts[1], ",")
	ranges := make([]Range, 0, len(rangeSpecs))

	for _, spec := range rangeSpecs {
		spec = strings.TrimSpace(spec)
		if spec == "" {
			continue
		}

		parts := strings.SplitN(spec, "-", 2)
		if len(parts) != 2 {
			continue
		}

		startStr, endStr := parts[0], parts[1]
		var start, end int64

		if startStr == "" {
			end, _ = strconv.ParseInt(endStr, 10, 64)
			start = fileSize - end
			end = fileSize - 1
		} else {
			start, _ = strconv.ParseInt(startStr, 10, 64)
			if endStr == "" {
				end = fileSize - 1
			} else {
				end, _ = strconv.ParseInt(endStr, 10, 64)
			}
		}

		if start < 0 {
			start = 0
		}
		if end >= fileSize {
			end = fileSize - 1
		}
		if start > end {
			continue
		}

		ranges = append(ranges, Range{Start: start, End: end})
	}

	return ranges, nil
}

func DownloadFile(c *gin.Context) {
	fileID := c.Param("file_id")
	versionID := c.Query("version_id")

	metadata, err := database.GetFileMetadata(fileID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "File not found"})
		return
	}

	if metadata.Status != models.UploadStatusComplete {
		c.JSON(http.StatusBadRequest, gin.H{"error": "File upload not completed"})
		return
	}

	c.Header("Accept-Ranges", "bytes")
	c.Header("Content-Disposition", "attachment; filename=\""+metadata.FileName+"\"")
	c.Header("Content-Type", metadata.FileType)

	if metadata.IsMerged && metadata.MergedManifestID != "" {
		fileData, err := seaweedfs.GetMergedFile(fileID, metadata.MergedManifestID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get merged file: " + err.Error()})
			return
		}
		c.Header("Content-Length", strconv.FormatInt(int64(len(fileData)), 10))
		c.Status(http.StatusOK)
		io.Copy(c.Writer, bytes.NewReader(fileData))
		return
	}

	stat, err := seaweedfs.SWClient.StatObject(c.Request.Context(), metadata.ObjectPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get file info"})
		return
	}

	fileSize := stat.Size
	rangeHeader := c.GetHeader("Range")
	ranges, err := parseRangeHeader(rangeHeader, fileSize)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid Range header"})
		return
	}

	if len(ranges) == 0 {
		if versionID != "" {
			obj, err := seaweedfs.SWClient.DownloadFileWithVersion(c.Request.Context(), metadata.ObjectPath, versionID)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to download file version"})
				return
			}
			defer obj.Close()
			io.Copy(c.Writer, obj)
			return
		}

		var obj *minio.Object
		if metadata.IsEncrypted && metadata.EncryptionKeyID != "" {
			obj, err = seaweedfs.SWClient.DownloadFileWithEncryption(c.Request.Context(), metadata.ObjectPath, metadata.EncryptionKeyID)
		} else {
			obj, err = seaweedfs.SWClient.DownloadFileS3(c.Request.Context(), metadata.ObjectPath)
		}
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to download file"})
			return
		}
		defer obj.Close()

		c.Header("Content-Length", strconv.FormatInt(fileSize, 10))
		c.Status(http.StatusOK)
		io.Copy(c.Writer, obj)
		return
	}

	if len(ranges) > 1 {
		var obj *minio.Object
		if metadata.IsEncrypted && metadata.EncryptionKeyID != "" {
			obj, err = seaweedfs.SWClient.DownloadFileWithEncryption(c.Request.Context(), metadata.ObjectPath, metadata.EncryptionKeyID)
		} else {
			obj, err = seaweedfs.SWClient.DownloadFileS3(c.Request.Context(), metadata.ObjectPath)
		}
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to download file"})
			return
		}
		defer obj.Close()

		c.Header("Content-Length", strconv.FormatInt(fileSize, 10))
		c.Status(http.StatusOK)
		io.Copy(c.Writer, obj)
		return
	}

	r := ranges[0]
	length := r.End - r.Start + 1

	opts := minio.GetObjectOptions{}
	opts.SetRange(r.Start, r.End)

	obj, err := seaweedfs.SWClient.GetS3Client().GetObject(c.Request.Context(), config.SeaweedFSBucketName, metadata.ObjectPath, opts)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to download file range"})
		return
	}
	defer obj.Close()

	c.Header("Content-Length", strconv.FormatInt(length, 10))
	c.Header("Content-Range", "bytes "+strconv.FormatInt(r.Start, 10)+"-"+
		strconv.FormatInt(r.End, 10)+"/"+strconv.FormatInt(fileSize, 10))
	c.Status(http.StatusPartialContent)

	io.CopyN(c.Writer, obj, length)
}

func DeleteFile(c *gin.Context) {
	fileID := c.Param("file_id")

	metadata, err := database.GetFileMetadata(fileID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "File not found"})
		return
	}

	metadata.RefCount--
	if metadata.RefCount > 0 {
		database.UpdateFileMetadata(metadata)
		c.JSON(http.StatusOK, gin.H{
			"message":   "Reference count decreased",
			"ref_count": metadata.RefCount,
		})
		return
	}

	if metadata.ObjectPath != "" {
		if err := seaweedfs.SWClient.DeleteObject(c.Request.Context(), metadata.ObjectPath); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete file from storage"})
			return
		}
	}

	if metadata.MD5Hash != "" {
		redis.DeleteFileMD5(c.Request.Context(), metadata.MD5Hash)
	}

	redis.DeleteChunkInfos(c.Request.Context(), fileID, metadata.TotalChunks)
	redis.DeleteUploadSession(c.Request.Context(), fileID)

	if err := database.DeleteChunkRecords(fileID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete chunk records"})
		return
	}

	if err := database.DeleteFileMetadata(fileID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete file metadata"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "File deleted successfully"})
}

func GetFileMetadata(c *gin.Context) {
	fileID := c.Param("file_id")

	metadata, err := database.GetFileMetadata(fileID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "File not found"})
		return
	}

	c.JSON(http.StatusOK, metadata)
}

func ListFiles(c *gin.Context) {
	var files []models.FileMetadata
	if err := database.DB.Find(&files).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to list files"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"files": files})
}

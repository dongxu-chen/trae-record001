package models

import (
	"time"

	"gorm.io/gorm"
)

type FileMetadata struct {
	ID               uint           `gorm:"primaryKey" json:"id"`
	FileID           string         `gorm:"uniqueIndex;size:64" json:"file_id"`
	FileName         string         `gorm:"size:255" json:"file_name"`
	FileSize         int64          `json:"file_size"`
	FileType         string         `gorm:"size:100" json:"file_type"`
	TotalChunks      int            `json:"total_chunks"`
	Status           string         `gorm:"size:20" json:"status"`
	ObjectPath       string         `gorm:"size:512" json:"object_path"`
	MD5Hash          string         `gorm:"size:32" json:"md5_hash"`
	EncryptionKeyID  string         `gorm:"size:64" json:"encryption_key_id"`
	IsEncrypted      bool           `json:"is_encrypted"`
	RefCount         int            `json:"ref_count" gorm:"default:1"`
	IsMerged         bool           `json:"is_merged" gorm:"default:false"`
	MergedManifestID string         `gorm:"size:128" json:"merged_manifest_id"`
	MergedObjectPath string         `gorm:"size:512" json:"merged_object_path"`
	CreatedAt        time.Time      `json:"created_at"`
	UpdatedAt        time.Time      `json:"updated_at"`
	DeletedAt        gorm.DeletedAt `gorm:"index" json:"-"`
}

type ChunkRecord struct {
	ID          uint      `gorm:"primaryKey" json:"id"`
	FileID      string    `gorm:"index;size:64" json:"file_id"`
	ChunkNumber int       `json:"chunk_number"`
	ChunkSize   int64     `json:"chunk_size"`
	ChunkPath   string    `gorm:"size:512" json:"chunk_path"`
	UploadedAt  time.Time `json:"uploaded_at"`
}

const (
	UploadStatusInit     = "init"
	UploadStatusUploading = "uploading"
	UploadStatusComplete  = "completed"
	UploadStatusFailed    = "failed"
)

package database

import (
	"cloud-storage-gateway/models"
	"log"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

var DB *gorm.DB

func InitDB() error {
	var err error
	DB, err = gorm.Open(sqlite.Open("file_storage.db"), &gorm.Config{})
	if err != nil {
		return err
	}

	err = DB.AutoMigrate(&models.FileMetadata{}, &models.ChunkRecord{})
	if err != nil {
		return err
	}

	log.Println("Database initialized successfully")
	return nil
}

func CreateFileMetadata(metadata *models.FileMetadata) error {
	return DB.Create(metadata).Error
}

func GetFileMetadata(fileID string) (*models.FileMetadata, error) {
	var metadata models.FileMetadata
	err := DB.Where("file_id = ?", fileID).First(&metadata).Error
	if err != nil {
		return nil, err
	}
	return &metadata, nil
}

func UpdateFileMetadata(metadata *models.FileMetadata) error {
	return DB.Save(metadata).Error
}

func DeleteFileMetadata(fileID string) error {
	return DB.Where("file_id = ?", fileID).Delete(&models.FileMetadata{}).Error
}

func CreateChunkRecord(record *models.ChunkRecord) error {
	return DB.Create(record).Error
}

func GetUploadedChunks(fileID string) ([]models.ChunkRecord, error) {
	var chunks []models.ChunkRecord
	err := DB.Where("file_id = ?", fileID).Order("chunk_number ASC").Find(&chunks).Error
	return chunks, err
}

func DeleteChunkRecords(fileID string) error {
	return DB.Where("file_id = ?", fileID).Delete(&models.ChunkRecord{}).Error
}

func IsChunkUploaded(fileID string, chunkNumber int) (bool, error) {
	var count int64
	err := DB.Model(&models.ChunkRecord{}).Where("file_id = ? AND chunk_number = ?", fileID, chunkNumber).Count(&count).Error
	return count > 0, err
}

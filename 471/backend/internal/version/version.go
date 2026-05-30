package version

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
	"gorm.io/gorm"

	"github.com/keymgmt/service/backend/internal/models"
	"github.com/keymgmt/service/backend/internal/vault"
	"github.com/keymgmt/service/backend/pkg/utils"
)

type VersionService struct {
	db          *gorm.DB
	vaultClient *vault.VaultClient
	log         *logrus.Logger
}

type DecryptWithVersionRequest struct {
	SecretID     string `json:"secret_id"`
	Version      int    `json:"version"`
	EncryptedData string `json:"encrypted_data"`
}

type VersionInfo struct {
	ID        uuid.UUID `json:"id"`
	Version   int       `json:"version"`
	CreatedAt time.Time `json:"created_at"`
	CreatedBy string    `json:"created_by"`
}

type DataDecryptResult struct {
	DecryptedValue string `json:"decrypted_value"`
	SecretVersion  int    `json:"secret_version"`
	DecryptedWith  string `json:"decrypted_with"`
}

func NewVersionService(db *gorm.DB, vaultClient *vault.VaultClient, log *logrus.Logger) *VersionService {
	return &VersionService{
		db:          db,
		vaultClient: vaultClient,
		log:         log,
	}
}

func (vs *VersionService) GetSecretVersions(ctx context.Context, secretID uuid.UUID) ([]VersionInfo, error) {
	var versions []models.SecretVersion
	if err := vs.db.Where("secret_id = ?", secretID).Order("version DESC").Find(&versions).Error; err != nil {
		vs.log.Errorf("Failed to get secret versions: %v", err)
		return nil, err
	}

	result := make([]VersionInfo, len(versions))
	for i, v := range versions {
		result[i] = VersionInfo{
			ID:        v.ID,
			Version:   v.Version,
			CreatedAt: v.CreatedAt,
			CreatedBy: v.CreatedBy,
		}
	}

	return result, nil
}

func (vs *VersionService) GetSpecificVersion(ctx context.Context, secretID uuid.UUID, version int) (*models.SecretVersion, error) {
	var secretVersion models.SecretVersion
	if err := vs.db.Where("secret_id = ? AND version = ?", secretID, version).First(&secretVersion).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, fmt.Errorf("version %d not found for secret %s", version, secretID)
		}
		vs.log.Errorf("Failed to get secret version: %v", err)
		return nil, err
	}

	return &secretVersion, nil
}

func (vs *VersionService) DecryptWithVersion(ctx context.Context, secretID uuid.UUID, version int, encryptedData string) (*DataDecryptResult, error) {
	secretVersion, err := vs.GetSpecificVersion(ctx, secretID, version)
	if err != nil {
		return nil, err
	}

	var decryptedValue string
	if vs.vaultClient != nil {
		plaintext, err := vs.vaultClient.Decrypt(ctx, "secrets-key", string(secretVersion.EncryptedValue))
		if err != nil {
			vs.log.Errorf("Failed to decrypt with vault: %v", err)
			return nil, fmt.Errorf("decryption failed: %w", err)
		}
		decryptedValue = string(plaintext)
	} else {
		var err error
		decryptedValue, err = utils.Decrypt(string(secretVersion.EncryptedValue))
		if err != nil {
			vs.log.Errorf("Failed to decrypt with local: %v", err)
			return nil, fmt.Errorf("decryption failed: %w", err)
		}
	}

	result := &DataDecryptResult{
		DecryptedValue: decryptedValue,
		SecretVersion:  version,
		DecryptedWith:  fmt.Sprintf("secret-%s-v%d", secretID.String()[:8], version),
	}

	vs.log.Infof("Decrypted data with secret %s version %d", secretID, version)
	return result, nil
}

func (vs *VersionService) DecryptHistoricalData(ctx context.Context, dataRecordID uuid.UUID) (*DataDecryptResult, error) {
	var record models.EncryptedDataRecord
	if err := vs.db.Where("id = ?", dataRecordID).First(&record).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, fmt.Errorf("data record not found: %s", dataRecordID)
		}
		return nil, err
	}

	return vs.DecryptWithVersion(ctx, record.SecretID, record.SecretVersion, record.DataReference)
}

func (vs *VersionService) RollbackToVersion(ctx context.Context, secretID uuid.UUID, targetVersion int, user string) error {
	secretVersion, err := vs.GetSpecificVersion(ctx, secretID, targetVersion)
	if err != nil {
		return err
	}

	tx := vs.db.Begin()
	if tx.Error != nil {
		return tx.Error
	}

	var currentSecret models.Secret
	if err := tx.Where("id = ?", secretID).First(&currentSecret).Error; err != nil {
		tx.Rollback()
		return err
	}

	newVersion := &models.SecretVersion{
		SecretID:       secretID,
		Version:        currentSecret.Version,
		EncryptedValue: currentSecret.EncryptedValue,
		CreatedAt:      currentSecret.UpdatedAt,
		CreatedBy:      user,
	}
	if err := tx.Create(newVersion).Error; err != nil {
		tx.Rollback()
		return err
	}

	currentSecret.EncryptedValue = secretVersion.EncryptedValue
	currentSecret.Version++
	currentSecret.UpdatedAt = time.Now()

	if err := tx.Save(&currentSecret).Error; err != nil {
		tx.Rollback()
		return err
	}

	tx.Commit()

	vs.log.Infof("Secret %s rolled back to version %d (new version: %d)", secretID, targetVersion, currentSecret.Version)
	return nil
}

func (vs *VersionService) CreateDataRecord(ctx context.Context, secretID uuid.UUID, secretVersion int, dataRef string, description string) (*models.EncryptedDataRecord, error) {
	record := &models.EncryptedDataRecord{
		SecretID:      secretID,
		SecretVersion: secretVersion,
		DataReference: dataRef,
		CreatedAt:     time.Now(),
		Description:   description,
	}

	if err := vs.db.Create(record).Error; err != nil {
		vs.log.Errorf("Failed to create data record: %v", err)
		return nil, err
	}

	return record, nil
}

func (vs *VersionService) GetDataRecords(ctx context.Context, secretID uuid.UUID, limit, offset int) ([]models.EncryptedDataRecord, int64, error) {
	var records []models.EncryptedDataRecord
	var total int64

	query := vs.db.Model(&models.EncryptedDataRecord{}).Where("secret_id = ?", secretID)

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	if err := query.Order("created_at DESC").Limit(limit).Offset(offset).Find(&records).Error; err != nil {
		return nil, 0, err
	}

	return records, total, nil
}

func (vs *VersionService) CompareVersions(ctx context.Context, secretID uuid.UUID, version1, version2 int) (map[string]interface{}, error) {
	v1, err := vs.GetSpecificVersion(ctx, secretID, version1)
	if err != nil {
		return nil, err
	}

	v2, err := vs.GetSpecificVersion(ctx, secretID, version2)
	if err != nil {
		return nil, err
	}

	var val1, val2 string
	if vs.vaultClient != nil {
		plaintext1, err := vs.vaultClient.Decrypt(ctx, "secrets-key", string(v1.EncryptedValue))
		if err == nil {
			val1 = string(plaintext1)
		}
		plaintext2, err := vs.vaultClient.Decrypt(ctx, "secrets-key", string(v2.EncryptedValue))
		if err == nil {
			val2 = string(plaintext2)
		}
	} else {
		val1, _ = utils.Decrypt(string(v1.EncryptedValue))
		val2, _ = utils.Decrypt(string(v2.EncryptedValue))
	}

	valueChanged := val1 != val2

	return map[string]interface{}{
		"secret_id":      secretID,
		"version_1":      version1,
		"version_2":      version2,
		"created_at_1":   v1.CreatedAt,
		"created_at_2":   v2.CreatedAt,
		"created_by_1":   v1.CreatedBy,
		"created_by_2":   v2.CreatedBy,
		"value_changed":  valueChanged,
		"days_between":   v2.CreatedAt.Sub(v1.CreatedAt).Hours() / 24,
	}, nil
}

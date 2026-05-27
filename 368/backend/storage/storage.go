package storage

import (
	"ssl-monitor/config"
	"ssl-monitor/models"

	"go.uber.org/zap"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

var DB *gorm.DB

func Init() {
	var err error

	DB, err = gorm.Open(sqlite.Open(config.Cfg.Database.DSN), &gorm.Config{})
	if err != nil {
		config.Logger.Fatal("初始化数据库失败", zap.Error(err))
	}

	err = DB.AutoMigrate(
		&models.Domain{},
		&models.CertRecord{},
		&models.AlertLog{},
		&models.AlgorithmRule{},
		&models.SubdomainRecord{},
		&models.DNSRecord{},
		&models.RuleUpdateLog{},
	)
	if err != nil {
		config.Logger.Fatal("数据库迁移失败", zap.Error(err))
	}

	config.Logger.Info("数据库初始化成功")
}

func GetDB() *gorm.DB {
	return DB
}

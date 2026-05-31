package logger

import (
	"redis-keyspace-notifier/config"
	"sync"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var (
	log  *zap.Logger
	once sync.Once
)

func Init() {
	once.Do(func() {
		zapConfig := zap.NewProductionConfig()
		zapConfig.EncoderConfig.TimeKey = "timestamp"
		zapConfig.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

		level := zap.InfoLevel
		switch config.AppConfig.LogLevel {
		case "debug":
			level = zap.DebugLevel
		case "warn":
			level = zap.WarnLevel
		case "error":
			level = zap.ErrorLevel
		}
		zapConfig.Level.SetLevel(level)

		var err error
		log, err = zapConfig.Build()
		if err != nil {
			panic(err)
		}
	})
}

func Info(msg string, fields ...zap.Field) {
	log.Info(msg, fields...)
}

func Debug(msg string, fields ...zap.Field) {
	log.Debug(msg, fields...)
}

func Warn(msg string, fields ...zap.Field) {
	log.Warn(msg, fields...)
}

func Error(msg string, fields ...zap.Field) {
	log.Error(msg, fields...)
}

func Fatal(msg string, fields ...zap.Field) {
	log.Fatal(msg, fields...)
}

func Sync() {
	_ = log.Sync()
}

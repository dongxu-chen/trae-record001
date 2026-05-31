package logger

import (
	"fmt"
	"log"
	"os"
	"strings"
	"time"
)

type Logger struct {
	level  string
	logger *log.Logger
}

const (
	LevelDebug = "debug"
	LevelInfo  = "info"
	LevelWarn  = "warn"
	LevelError = "error"
)

func New(level string) *Logger {
	return &Logger{
		level:  strings.ToLower(level),
		logger: log.New(os.Stdout, "", 0),
	}
}

func (l *Logger) log(level, format string, args ...interface{}) {
	if !l.shouldLog(level) {
		return
	}
	timestamp := time.Now().Format("2006-01-02 15:04:05.000")
	msg := fmt.Sprintf(format, args...)
	l.logger.Printf("[%s] [%s] %s", timestamp, strings.ToUpper(level), msg)
}

func (l *Logger) shouldLog(level string) bool {
	levels := map[string]int{
		LevelDebug: 0,
		LevelInfo:  1,
		LevelWarn:  2,
		LevelError: 3,
	}
	return levels[level] >= levels[l.level]
}

func (l *Logger) Debug(format string, args ...interface{}) {
	l.log(LevelDebug, format, args...)
}

func (l *Logger) Info(format string, args ...interface{}) {
	l.log(LevelInfo, format, args...)
}

func (l *Logger) Warn(format string, args ...interface{}) {
	l.log(LevelWarn, format, args...)
}

func (l *Logger) Error(format string, args ...interface{}) {
	l.log(LevelError, format, args...)
}

package utils

import (
	"log"
	"os"
)

type Logger struct {
	debug   *log.Logger
	info    *log.Logger
	warning *log.Logger
	error   *log.Logger
	level   string
}

func NewLogger(level string) *Logger {
	return &Logger{
		debug:   log.New(os.Stdout, "[DEBUG] ", log.Ldate|log.Ltime|log.Lshortfile),
		info:    log.New(os.Stdout, "[INFO] ", log.Ldate|log.Ltime),
		warning: log.New(os.Stdout, "[WARN] ", log.Ldate|log.Ltime),
		error:   log.New(os.Stderr, "[ERROR] ", log.Ldate|log.Ltime|log.Lshortfile),
		level:   level,
	}
}

func (l *Logger) Debug(format string, v ...interface{}) {
	if l.level == "debug" {
		l.debug.Printf(format, v...)
	}
}

func (l *Logger) Info(format string, v ...interface{}) {
	if l.level == "debug" || l.level == "info" {
		l.info.Printf(format, v...)
	}
}

func (l *Logger) Warning(format string, v ...interface{}) {
	if l.level != "error" {
		l.warning.Printf(format, v...)
	}
}

func (l *Logger) Error(format string, v ...interface{}) {
	l.error.Printf(format, v...)
}

func (l *Logger) Fatal(format string, v ...interface{}) {
	l.error.Fatalf(format, v...)
}

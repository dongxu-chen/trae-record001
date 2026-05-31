package processor

import (
	"redis-keyspace-notifier/config"
	"redis-keyspace-notifier/models"
	"strings"
)

type EventFilter struct{}

func NewEventFilter() *EventFilter {
	return &EventFilter{}
}

func (f *EventFilter) Filter(event *models.KeyEvent) bool {
	if !config.AppConfig.Filter.Enabled {
		return true
	}

	if !f.filterByEventType(event.EventType) {
		return false
	}

	if !f.filterByKeyPrefix(event.Key) {
		return false
	}

	return true
}

func (f *EventFilter) filterByEventType(eventType string) bool {
	if len(config.AppConfig.Filter.EventTypes) == 0 {
		return true
	}

	for _, allowedType := range config.AppConfig.Filter.EventTypes {
		if eventType == allowedType {
			return true
		}
	}

	return false
}

func (f *EventFilter) filterByKeyPrefix(key string) bool {
	if len(config.AppConfig.Filter.IncludePrefix) > 0 {
		included := false
		for _, prefix := range config.AppConfig.Filter.IncludePrefix {
			if strings.HasPrefix(key, prefix) {
				included = true
				break
			}
		}
		if !included {
			return false
		}
	}

	for _, prefix := range config.AppConfig.Filter.ExcludePrefix {
		if strings.HasPrefix(key, prefix) {
			return false
		}
	}

	return true
}

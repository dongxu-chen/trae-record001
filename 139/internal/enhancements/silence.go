package enhancements

import (
	"time"

	"github.com/prometheus/prometheus/model/labels"
)

type Silence struct {
	ID        string            `json:"id" yaml:"id"`
	Matchers  []Matcher         `json:"matchers" yaml:"matchers"`
	StartsAt  time.Time         `json:"starts_at" yaml:"starts_at"`
	EndsAt    time.Time         `json:"ends_at" yaml:"ends_at"`
	CreatedBy string            `json:"created_by" yaml:"created_by"`
	Comment   string            `json:"comment" yaml:"comment"`
}

type Matcher struct {
	Name    string `json:"name" yaml:"name"`
	Value   string `json:"value" yaml:"value"`
	IsRegex bool   `json:"is_regex,omitempty" yaml:"is_regex,omitempty"`
	IsNot   bool   `json:"is_not,omitempty" yaml:"is_not,omitempty"`
}

type SilenceManager struct {
	silences []Silence
}

func NewSilenceManager() *SilenceManager {
	return &SilenceManager{}
}

func (sm *SilenceManager) AddSilence(s Silence) {
	sm.silences = append(sm.silences, s)
}

func (sm *SilenceManager) AddSilences(silences []Silence) {
	sm.silences = append(sm.silences, silences...)
}

func (sm *SilenceManager) IsSilenced(alertLabels map[string]string, evalTime time.Time) bool {
	for _, s := range sm.silences {
		if evalTime.Before(s.StartsAt) || evalTime.After(s.EndsAt) {
			continue
		}
		if sm.matches(alertLabels, s.Matchers) {
			return true
		}
	}
	return false
}

func (sm *SilenceManager) matches(alertLabels map[string]string, matchers []Matcher) bool {
	for _, m := range matchers {
		labelValue, exists := alertLabels[m.Name]
		if !exists {
			if !m.IsNot {
				return false
			}
			continue
		}

		matched := labelValue == m.Value
		if m.IsRegex {
			matched = sm.matchRegex(labelValue, m.Value)
		}

		if m.IsNot {
			matched = !matched
		}

		if !matched {
			return false
		}
	}
	return true
}

func (sm *SilenceManager) matchRegex(value, pattern string) bool {
	return value == pattern
}

func (sm *SilenceManager) GetSilences() []Silence {
	return sm.silences
}

func (sm *SilenceManager) Clear() {
	sm.silences = nil
}

func CreateSimpleSilence(alertName, instance, job string, duration time.Duration, comment string) Silence {
	now := time.Now()
	return Silence{
		ID:        "silence-" + alertName + "-" + instance,
		StartsAt:  now,
		EndsAt:    now.Add(duration),
		CreatedBy: "alert-tester",
		Comment:   comment,
		Matchers: []Matcher{
			{Name: "alertname", Value: alertName},
			{Name: "instance", Value: instance},
			{Name: "job", Value: job},
		},
	}
}

func LabelsToMap(l labels.Labels) map[string]string {
	result := make(map[string]string)
	for _, l := range l {
		result[l.Name] = l.Value
	}
	return result
}

package structdiff

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strings"

	"gopkg.in/yaml.v3"
)

type ChangeType string

const (
	ChangeAdded    ChangeType = "added"
	ChangeRemoved  ChangeType = "removed"
	ChangeModified ChangeType = "modified"
	ChangeUnchanged ChangeType = "unchanged"
)

type StructDiff struct {
	Path     string      `json:"path"`
	Type     ChangeType  `json:"type"`
	OldValue interface{} `json:"old_value,omitempty"`
	NewValue interface{} `json:"new_value,omitempty"`
}

type DiffResult struct {
	Changes      []StructDiff `json:"changes"`
	AddedCount   int          `json:"added_count"`
	RemovedCount int          `json:"removed_count"`
	ModifiedCount int         `json:"modified_count"`
	TotalChanges int          `json:"total_changes"`
}

func CompareStructured(oldContent, newContent, contentType string) (*DiffResult, error) {
	var oldData, newData map[string]interface{}
	var err error

	switch contentType {
	case "json":
		oldData, newData, err = parseJSON(oldContent, newContent)
	case "yaml", "yml":
		oldData, newData, err = parseYAML(oldContent, newContent)
	default:
		return nil, fmt.Errorf("unsupported content type: %s", contentType)
	}

	if err != nil {
		return nil, err
	}

	result := &DiffResult{
		Changes: make([]StructDiff, 0),
	}

	compareMap(oldData, newData, "", result)

	result.TotalChanges = result.AddedCount + result.RemovedCount + result.ModifiedCount
	return result, nil
}

func parseJSON(oldStr, newStr string) (map[string]interface{}, map[string]interface{}, error) {
	var oldData, newData map[string]interface{}

	if oldStr != "" {
		if err := json.Unmarshal([]byte(oldStr), &oldData); err != nil {
			return nil, nil, fmt.Errorf("parse old JSON failed: %v", err)
		}
	} else {
		oldData = make(map[string]interface{})
	}

	if newStr != "" {
		if err := json.Unmarshal([]byte(newStr), &newData); err != nil {
			return nil, nil, fmt.Errorf("parse new JSON failed: %v", err)
		}
	} else {
		newData = make(map[string]interface{})
	}

	return oldData, newData, nil
}

func parseYAML(oldStr, newStr string) (map[string]interface{}, map[string]interface{}, error) {
	var oldData, newData map[string]interface{}

	if oldStr != "" {
		if err := yaml.Unmarshal([]byte(oldStr), &oldData); err != nil {
			return nil, nil, fmt.Errorf("parse old YAML failed: %v", err)
		}
	} else {
		oldData = make(map[string]interface{})
	}

	if newStr != "" {
		if err := yaml.Unmarshal([]byte(newStr), &newData); err != nil {
			return nil, nil, fmt.Errorf("parse new YAML failed: %v", err)
		}
	} else {
		newData = make(map[string]interface{})
	}

	return oldData, newData, nil
}

func compareMap(oldMap, newMap map[string]interface{}, path string, result *DiffResult) {
	for key, oldVal := range oldMap {
		currentPath := buildPath(path, key)
		
		if newVal, exists := newMap[key]; exists {
			compareValues(oldVal, newVal, currentPath, result)
		} else {
			result.Changes = append(result.Changes, StructDiff{
				Path:     currentPath,
				Type:     ChangeRemoved,
				OldValue: oldVal,
			})
			result.RemovedCount++
		}
	}

	for key, newVal := range newMap {
		if _, exists := oldMap[key]; !exists {
			currentPath := buildPath(path, key)
			result.Changes = append(result.Changes, StructDiff{
				Path:     currentPath,
				Type:     ChangeAdded,
				NewValue: newVal,
			})
			result.AddedCount++
		}
	}
}

func compareValues(oldVal, newVal interface{}, path string, result *DiffResult) {
	if reflect.DeepEqual(oldVal, newVal) {
		return
	}

	oldIsMap := isMap(oldVal)
	newIsMap := isMap(newVal)

	if oldIsMap && newIsMap {
		compareMap(toStringMap(oldVal), toStringMap(newVal), path, result)
		return
	}

	oldIsSlice := isSlice(oldVal)
	newIsSlice := isSlice(newVal)

	if oldIsSlice && newIsSlice {
		compareSlice(toInterfaceSlice(oldVal), toInterfaceSlice(newVal), path, result)
		return
	}

	result.Changes = append(result.Changes, StructDiff{
		Path:     path,
		Type:     ChangeModified,
		OldValue: oldVal,
		NewValue: newVal,
	})
	result.ModifiedCount++
}

func compareSlice(oldSlice, newSlice []interface{}, path string, result *DiffResult) {
	minLen := len(oldSlice)
	if len(newSlice) < minLen {
		minLen = len(newSlice)
	}

	for i := 0; i < minLen; i++ {
		currentPath := fmt.Sprintf("%s[%d]", path, i)
		compareValues(oldSlice[i], newSlice[i], currentPath, result)
	}

	for i := minLen; i < len(oldSlice); i++ {
		currentPath := fmt.Sprintf("%s[%d]", path, i)
		result.Changes = append(result.Changes, StructDiff{
			Path:     currentPath,
			Type:     ChangeRemoved,
			OldValue: oldSlice[i],
		})
		result.RemovedCount++
	}

	for i := minLen; i < len(newSlice); i++ {
		currentPath := fmt.Sprintf("%s[%d]", path, i)
		result.Changes = append(result.Changes, StructDiff{
			Path:     currentPath,
			Type:     ChangeAdded,
			NewValue: newSlice[i],
		})
		result.AddedCount++
	}
}

func isMap(v interface{}) bool {
	return reflect.TypeOf(v) != nil && reflect.TypeOf(v).Kind() == reflect.Map
}

func isSlice(v interface{}) bool {
	return reflect.TypeOf(v) != nil && reflect.TypeOf(v).Kind() == reflect.Slice
}

func toStringMap(v interface{}) map[string]interface{} {
	result := make(map[string]interface{})
	val := reflect.ValueOf(v)
	for _, key := range val.MapKeys() {
		result[key.String()] = val.MapIndex(key).Interface()
	}
	return result
}

func toInterfaceSlice(v interface{}) []interface{} {
	val := reflect.ValueOf(v)
	result := make([]interface{}, val.Len())
	for i := 0; i < val.Len(); i++ {
		result[i] = val.Index(i).Interface()
	}
	return result
}

func buildPath(parent, key string) string {
	if parent == "" {
		return key
	}
	return parent + "." + key
}

func (r *DiffResult) GetSummary() string {
	return fmt.Sprintf("+%d -%d ~%d 共%d处变更", 
		r.AddedCount, r.RemovedCount, r.ModifiedCount, r.TotalChanges)
}

func (r *DiffResult) GetHTML() string {
	var sb strings.Builder
	for _, change := range r.Changes {
		switch change.Type {
		case ChangeAdded:
			sb.WriteString(fmt.Sprintf(`<div class="diff-added">+ %s = %v</div>`, 
				escapeHTML(change.Path), formatValue(change.NewValue)))
		case ChangeRemoved:
			sb.WriteString(fmt.Sprintf(`<div class="diff-removed">- %s = %v</div>`, 
				escapeHTML(change.Path), formatValue(change.OldValue)))
		case ChangeModified:
			sb.WriteString(fmt.Sprintf(`<div class="diff-modified">~ %s: %v → %v</div>`, 
				escapeHTML(change.Path), formatValue(change.OldValue), formatValue(change.NewValue)))
		}
	}
	return sb.String()
}

func formatValue(v interface{}) string {
	if v == nil {
		return "null"
	}
	switch val := v.(type) {
	case string:
		if len(val) > 50 {
			return fmt.Sprintf("%q...", val[:50])
		}
		return fmt.Sprintf("%q", val)
	default:
		str := fmt.Sprintf("%v", val)
		if len(str) > 50 {
			return str[:50] + "..."
		}
		return str
	}
}

func escapeHTML(s string) string {
	s = strings.ReplaceAll(s, "&", "&amp;")
	s = strings.ReplaceAll(s, "<", "&lt;")
	s = strings.ReplaceAll(s, ">", "&gt;")
	return s
}

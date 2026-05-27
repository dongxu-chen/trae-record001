package output

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"

	"github.com/sirupsen/logrus"

	"container-security-monitor/pkg/config"
	"container-security-monitor/pkg/detector"
)

type Output interface {
	Send(alert *detector.SecurityAlert) error
}

type Manager struct {
	outputs []Output
}

func NewManager(outputConfigs []config.OutputConfig) (*Manager, error) {
	manager := &Manager{}

	for _, cfg := range outputConfigs {
		var output Output
		var err error

		switch cfg.Type {
		case "stdout":
			output = NewStdoutOutput()
		case "file":
			output, err = NewFileOutput(cfg.Config["path"])
		case "webhook":
			output, err = NewWebhookOutput(cfg.Config["url"])
		default:
			logrus.Warnf("Unknown output type: %s", cfg.Type)
			continue
		}

		if err != nil {
			return nil, err
		}

		manager.outputs = append(manager.outputs, output)
	}

	return manager, nil
}

func (m *Manager) Send(alert *detector.SecurityAlert) {
	for _, output := range m.outputs {
		if err := output.Send(alert); err != nil {
			logrus.Errorf("Failed to send alert: %v", err)
		}
	}
}

type StdoutOutput struct{}

func NewStdoutOutput() *StdoutOutput {
	return &StdoutOutput{}
}

func (s *StdoutOutput) Send(alert *detector.SecurityAlert) error {
	data, err := json.MarshalIndent(alert, "", "  ")
	if err != nil {
		return err
	}
	fmt.Println(string(data))
	return nil
}

type FileOutput struct {
	path string
	file *os.File
}

func NewFileOutput(path string) (*FileOutput, error) {
	file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return nil, err
	}
	return &FileOutput{path: path, file: file}, nil
}

func (f *FileOutput) Send(alert *detector.SecurityAlert) error {
	data, err := json.Marshal(alert)
	if err != nil {
		return err
	}
	_, err = f.file.WriteString(string(data) + "\n")
	return err
}

type WebhookOutput struct {
	url string
}

func NewWebhookOutput(url string) (*WebhookOutput, error) {
	return &WebhookOutput{url: url}, nil
}

func (w *WebhookOutput) Send(alert *detector.SecurityAlert) error {
	data, err := json.Marshal(alert)
	if err != nil {
		return err
	}

	resp, err := http.Post(w.url, "application/json", bytes.NewBuffer(data))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("webhook returned status: %d", resp.StatusCode)
	}

	return nil
}

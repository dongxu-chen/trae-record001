package secrets

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/sirupsen/logrus"
)

type Secret struct {
	Name  string
	Value string
}

type SecretManager struct {
	log            *logrus.Logger
	secrets        map[string]*Secret
	mu             sync.RWMutex
	apiBaseURL     string
	apiToken       string
	watchPaths     []string
	pollInterval   time.Duration
	watcher        *fsnotify.Watcher
	callbacks      []func(map[string]*Secret)
	lastUpdate     time.Time
	updateCount    int64
}

type Config struct {
	APIBaseURL   string
	APIToken     string
	WatchPaths   []string
	PollInterval time.Duration
}

func NewSecretManager(log *logrus.Logger, cfg Config) *SecretManager {
	if cfg.PollInterval == 0 {
		cfg.PollInterval = 30 * time.Second
	}

	return &SecretManager{
		log:          log,
		secrets:      make(map[string]*Secret),
		apiBaseURL:   cfg.APIBaseURL,
		apiToken:     cfg.APIToken,
		watchPaths:   cfg.WatchPaths,
		pollInterval: cfg.PollInterval,
	}
}

func (sm *SecretManager) Start(ctx context.Context) error {
	sm.log.Info("Starting secret manager")

	if err := sm.loadFromFiles(); err != nil {
		sm.log.Errorf("Failed to load secrets from files: %v", err)
	}

	if sm.apiBaseURL != "" {
		if err := sm.loadFromAPI(ctx); err != nil {
			sm.log.Errorf("Failed to load secrets from API: %v", err)
		}
	}

	if len(sm.watchPaths) > 0 {
		if err := sm.startFileWatcher(); err != nil {
			sm.log.Errorf("Failed to start file watcher: %v", err)
		}
	}

	go sm.pollLoop(ctx)

	sm.log.Infof("Secret manager started with %d secrets", len(sm.secrets))
	return nil
}

func (sm *SecretManager) Stop() {
	sm.log.Info("Stopping secret manager")
	if sm.watcher != nil {
		sm.watcher.Close()
	}
}

func (sm *SecretManager) GetSecret(name string) (*Secret, bool) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	secret, exists := sm.secrets[name]
	return secret, exists
}

func (sm *SecretManager) GetAllSecrets() map[string]*Secret {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	result := make(map[string]*Secret, len(sm.secrets))
	for k, v := range sm.secrets {
		result[k] = &Secret{
			Name:  v.Name,
			Value: v.Value,
		}
	}
	return result
}

func (sm *SecretManager) OnUpdate(callback func(map[string]*Secret)) {
	sm.callbacks = append(sm.callbacks, callback)
}

func (sm *SecretManager) Stats() (int, time.Time, int64) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return len(sm.secrets), sm.lastUpdate, sm.updateCount
}

func (sm *SecretManager) loadFromFiles() error {
	sm.log.Infof("Loading secrets from %d paths", len(sm.watchPaths))

	secrets := make(map[string]*Secret)

	for _, path := range sm.watchPaths {
		info, err := os.Stat(path)
		if err != nil {
			sm.log.Warnf("Path not accessible: %s, error: %v", path, err)
			continue
		}

		if info.IsDir() {
			err := filepath.Walk(path, func(filePath string, fileInfo os.FileInfo, err error) error {
				if err != nil {
					return err
				}
				if fileInfo.IsDir() {
					return nil
				}
				return sm.loadSecretFile(filePath, secrets)
			})
			if err != nil {
				sm.log.Errorf("Failed to walk directory %s: %v", path, err)
			}
		} else {
			if err := sm.loadSecretFile(path, secrets); err != nil {
				sm.log.Errorf("Failed to load file %s: %v", path, err)
			}
		}
	}

	sm.updateSecrets(secrets)
	return nil
}

func (sm *SecretManager) loadSecretFile(filePath string, secrets map[string]*Secret) error {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return err
	}

	name := filepath.Base(filePath)
	name = strings.TrimSuffix(name, filepath.Ext(name))

	secrets[name] = &Secret{
		Name:  name,
		Value: string(content),
	}

	sm.log.Debugf("Loaded secret from file: %s", name)
	return nil
}

func (sm *SecretManager) loadFromAPI(ctx context.Context) error {
	sm.log.Info("Loading secrets from API")

	url := fmt.Sprintf("%s/api/v1/secrets?limit=1000", sm.apiBaseURL)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("X-User", "sidecar-proxy")
	if sm.apiToken != "" {
		req.Header.Set("Authorization", "Bearer "+sm.apiToken)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API request failed: %s, body: %s", resp.Status, string(body))
	}

	var result struct {
		Secrets []struct {
			ID   string `json:"id"`
			Name string `json:"name"`
		} `json:"secrets"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return err
	}

	secrets := make(map[string]*Secret)
	for _, s := range result.Secrets {
		value, err := sm.fetchSecretValue(ctx, s.ID)
		if err != nil {
			sm.log.Errorf("Failed to fetch secret %s: %v", s.Name, err)
			continue
		}
		secrets[s.Name] = &Secret{
			Name:  s.Name,
			Value: value,
		}
	}

	sm.updateSecrets(secrets)
	return nil
}

func (sm *SecretManager) fetchSecretValue(ctx context.Context, secretID string) (string, error) {
	url := fmt.Sprintf("%s/api/v1/secrets/%s", sm.apiBaseURL, secretID)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("X-User", "sidecar-proxy")
	if sm.apiToken != "" {
		req.Header.Set("Authorization", "Bearer "+sm.apiToken)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("API request failed: %s", resp.Status)
	}

	var result struct {
		Value string `json:"value"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	return result.Value, nil
}

func (sm *SecretManager) updateSecrets(newSecrets map[string]*Secret) {
	sm.mu.Lock()
	sm.secrets = newSecrets
	sm.lastUpdate = time.Now()
	sm.updateCount++
	sm.mu.Unlock()

	if len(sm.callbacks) > 0 {
		allSecrets := sm.GetAllSecrets()
		for _, cb := range sm.callbacks {
			go cb(allSecrets)
		}
	}

	sm.log.Infof("Secrets updated: %d total", len(newSecrets))
}

func (sm *SecretManager) startFileWatcher() error {
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return err
	}

	sm.watcher = watcher

	for _, path := range sm.watchPaths {
		if err := watcher.Add(path); err != nil {
			sm.log.Errorf("Failed to watch path %s: %v", path, err)
		} else {
			sm.log.Infof("Watching path for changes: %s", path)
		}
	}

	go func() {
		for {
			select {
			case event, ok := <-watcher.Events:
				if !ok {
					return
				}
				if event.Op&(fsnotify.Write|fsnotify.Create|fsnotify.Remove) != 0 {
					sm.log.Infof("File change detected: %s, op: %s", event.Name, event.Op)
					if err := sm.loadFromFiles(); err != nil {
						sm.log.Errorf("Failed to reload secrets: %v", err)
					}
				}
			case err, ok := <-watcher.Errors:
				if !ok {
					return
				}
				sm.log.Errorf("Watcher error: %v", err)
			}
		}
	}()

	return nil
}

func (sm *SecretManager) pollLoop(ctx context.Context) {
	ticker := time.NewTicker(sm.pollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			if sm.apiBaseURL != "" {
				if err := sm.loadFromAPI(ctx); err != nil {
					sm.log.Errorf("Polling failed: %v", err)
				}
			}
		case <-ctx.Done():
			return
		}
	}
}

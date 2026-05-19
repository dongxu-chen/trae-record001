package function

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

type EventTrigger struct {
	client          *kubernetes.Clientset
	gatewayURL      string
	functionName    string
	namespaces      []string
	dedupWindow     int
	eventCache      map[string]time.Time
	cacheMutex      sync.RWMutex
	watchers        []watch.Interface
	ctx             context.Context
	cancel          context.CancelFunc
}

type K8sEvent struct {
	Type   string      `json:"type"`
	Object interface{} `json:"object"`
}

var trigger *EventTrigger
var once sync.Once

func NewEventTrigger() (*EventTrigger, error) {
	config, err := rest.InClusterConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to get in-cluster config: %v", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8s client: %v", err)
	}

	gatewayURL := os.Getenv("OPENFAAS_GATEWAY")
	if gatewayURL == "" {
		gatewayURL = "http://gateway.openfaas:8080"
	}

	functionName := os.Getenv("FUNCTION_NAME")
	if functionName == "" {
		functionName = "k8s-event-handler-python"
	}

	namespacesStr := os.Getenv("EVENT_NAMESPACES")
	var namespaces []string
	if namespacesStr != "" {
		namespaces = strings.Split(namespacesStr, ",")
	} else {
		namespaces = []string{"default"}
	}

	dedupWindow := 300
	if window := os.Getenv("EVENT_DEDUP_WINDOW"); window != "" {
		if w, err := time.ParseDuration(window); err == nil {
			dedupWindow = int(w.Seconds())
		}
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &EventTrigger{
		client:       clientset,
		gatewayURL:   gatewayURL,
		functionName: functionName,
		namespaces:   namespaces,
		dedupWindow:  dedupWindow,
		eventCache:   make(map[string]time.Time),
		ctx:          ctx,
		cancel:       cancel,
	}, nil
}

func (t *EventTrigger) Start() {
	fmt.Printf("Starting Kubernetes Event Trigger for namespaces: %v\n", t.namespaces)

	for _, ns := range t.namespaces {
		go t.watchNamespace(ns)
	}

	go t.cleanupCache()
}

func (t *EventTrigger) watchNamespace(namespace string) {
	for {
		select {
		case <-t.ctx.Done():
			fmt.Printf("Stopping watch for namespace: %s\n", namespace)
			return
		default:
			watcher, err := t.client.CoreV1().Events(namespace).Watch(t.ctx, metav1.ListOptions{})
			if err != nil {
				fmt.Printf("Error watching events in %s: %v, retrying in 5s\n", namespace, err)
				time.Sleep(5 * time.Second)
				continue
			}

			fmt.Printf("Started watching events in namespace: %s\n", namespace)
			t.cacheMutex.Lock()
			t.watchers = append(t.watchers, watcher)
			t.cacheMutex.Unlock()

			for event := range watcher.ResultChan() {
				t.handleEvent(event)
			}

			fmt.Printf("Watch channel closed for %s, reconnecting...\n", namespace)
			time.Sleep(2 * time.Second)
		}
	}
}

func (t *EventTrigger) handleEvent(event watch.Event) {
	eventJSON, err := json.Marshal(event)
	if err != nil {
		fmt.Printf("Error marshaling event: %v\n", err)
		return
	}

	var k8sEvent K8sEvent
	if err := json.Unmarshal(eventJSON, &k8sEvent); err != nil {
		fmt.Printf("Error unmarshaling event: %v\n", err)
		return
	}

	eventKey := t.generateEventKey(k8sEvent)

	t.cacheMutex.RLock()
	lastSeen, exists := t.eventCache[eventKey]
	t.cacheMutex.RUnlock()

	now := time.Now()
	if exists && now.Sub(lastSeen).Seconds() < float64(t.dedupWindow) {
		fmt.Printf("Deduplicated event: %s (last seen %v ago)\n", eventKey, now.Sub(lastSeen))
		return
	}

	t.cacheMutex.Lock()
	t.eventCache[eventKey] = now
	t.cacheMutex.Unlock()

	fmt.Printf("Triggering function for event: %s\n", eventKey)
	go t.invokeFunction(eventJSON)
}

func (t *EventTrigger) generateEventKey(event K8sEvent) string {
	obj, ok := event.Object.(map[string]interface{})
	if !ok {
		return fmt.Sprintf("%d", time.Now().UnixNano())
	}

	metadata, _ := obj["metadata"].(map[string]interface{})
	involved, _ := obj["involvedObject"].(map[string]interface{})

	namespace := ""
	if ns, ok := metadata["namespace"].(string); ok {
		namespace = ns
	}
	if ns, ok := involved["namespace"].(string); ok && namespace == "" {
		namespace = ns
	}

	name := ""
	if n, ok := metadata["name"].(string); ok {
		name = n
	}
	if n, ok := involved["name"].(string); ok && name == "" {
		name = n
	}

	reason, _ := obj["reason"].(string)
	eventType, _ := obj["type"].(string)

	return fmt.Sprintf("%s:%s:%s:%s", namespace, name, reason, eventType)
}

func (t *EventTrigger) invokeFunction(eventData []byte) {
	url := fmt.Sprintf("%s/function/%s", t.gatewayURL, t.functionName)

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(eventData))
	if err != nil {
		fmt.Printf("Error creating request: %v\n", err)
		return
	}

	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("Error invoking function: %v\n", err)
		return
	}
	defer resp.Body.Close()

	fmt.Printf("Function invoked, status: %d\n", resp.StatusCode)
}

func (t *EventTrigger) cleanupCache() {
	ticker := time.NewTicker(time.Duration(t.dedupWindow) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-t.ctx.Done():
			return
		case <-ticker.C:
			t.cacheMutex.Lock()
			now := time.Now()
			for key, lastSeen := range t.eventCache {
				if now.Sub(lastSeen).Seconds() > float64(t.dedupWindow)*2 {
					delete(t.eventCache, key)
				}
			}
			fmt.Printf("Cache cleanup complete, current size: %d\n", len(t.eventCache))
			t.cacheMutex.Unlock()
		}
	}
}

func (t *EventTrigger) Stop() {
	t.cancel()
	t.cacheMutex.Lock()
	for _, w := range t.watchers {
		w.Stop()
	}
	t.cacheMutex.Unlock()
}

func initTrigger() {
	var err error
	trigger, err = NewEventTrigger()
	if err != nil {
		fmt.Printf("Warning: Failed to initialize trigger: %v\n", err)
		fmt.Println("Running in health check mode only")
		return
	}
	trigger.Start()
}

func Handle(req []byte) string {
	once.Do(initTrigger)

	status := map[string]interface{}{
		"status":   "running",
		"function": trigger.functionName,
		"gateway":  trigger.gatewayURL,
		"cache_size": func() int {
			trigger.cacheMutex.RLock()
			defer trigger.cacheMutex.RUnlock()
			return len(trigger.eventCache)
		}(),
	}

	response, _ := json.Marshal(status)
	return string(response)
}

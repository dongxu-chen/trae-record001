package watcher

import (
	"log"
	"path/filepath"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
)

type FileChangeEvent struct {
	Path      string
	Operation string
	Timestamp time.Time
}

type Watcher struct {
	watcher      *fsnotify.Watcher
	watchDirs    map[string]bool
	eventChan    chan FileChangeEvent
	stopChan     chan struct{}
	debounceDur  time.Duration
	eventBuffer  map[string]time.Time
	bufferMu     sync.Mutex
	flushTicker  *time.Ticker
	onFileChange func(event FileChangeEvent)
}

type WatcherOption func(*Watcher)

func WithDebounceDuration(d time.Duration) WatcherOption {
	return func(w *Watcher) {
		w.debounceDur = d
	}
}

func WithOnFileChange(fn func(event FileChangeEvent)) WatcherOption {
	return func(w *Watcher) {
		w.onFileChange = fn
	}
}

func NewWatcher(opts ...WatcherOption) (*Watcher, error) {
	fsWatcher, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, err
	}

	w := &Watcher{
		watcher:     fsWatcher,
		watchDirs:   make(map[string]bool),
		eventChan:   make(chan FileChangeEvent, 100),
		stopChan:    make(chan struct{}),
		debounceDur: 500 * time.Millisecond,
		eventBuffer: make(map[string]time.Time),
	}

	for _, opt := range opts {
		opt(w)
	}

	go w.run()
	go w.flushEvents()

	return w, nil
}

func (w *Watcher) Add(path string) error {
	absPath, err := filepath.Abs(path)
	if err != nil {
		return err
	}

	if w.watchDirs[absPath] {
		return nil
	}

	if err := w.watcher.Add(absPath); err != nil {
		return err
	}

	w.watchDirs[absPath] = true
	return nil
}

func (w *Watcher) Remove(path string) error {
	absPath, err := filepath.Abs(path)
	if err != nil {
		return err
	}

	if !w.watchDirs[absPath] {
		return nil
	}

	if err := w.watcher.Remove(absPath); err != nil {
		return err
	}

	delete(w.watchDirs, absPath)
	return nil
}

func (w *Watcher) WatchDirs() []string {
	dirs := make([]string, 0, len(w.watchDirs))
	for dir := range w.watchDirs {
		dirs = append(dirs, dir)
	}
	return dirs
}

func (w *Watcher) Events() <-chan FileChangeEvent {
	return w.eventChan
}

func (w *Watcher) Close() error {
	close(w.stopChan)
	if w.flushTicker != nil {
		w.flushTicker.Stop()
	}
	return w.watcher.Close()
}

func (w *Watcher) run() {
	for {
		select {
		case <-w.stopChan:
			return
		case event, ok := <-w.watcher.Events:
			if !ok {
				return
			}
			w.handleEvent(event)
		case err, ok := <-w.watcher.Errors:
			if !ok {
				return
			}
			log.Printf("watcher error: %v", err)
		}
	}
}

func (w *Watcher) handleEvent(event fsnotify.Event) {
	op := w.getOperationString(event.Op)
	if op == "" {
		return
	}

	w.bufferMu.Lock()
	defer w.bufferMu.Unlock()

	key := event.Name + ":" + op
	w.eventBuffer[key] = time.Now()
}

func (w *Watcher) flushEvents() {
	w.flushTicker = time.NewTicker(100 * time.Millisecond)
	defer w.flushTicker.Stop()

	for {
		select {
		case <-w.stopChan:
			return
		case <-w.flushTicker.C:
			w.processBufferedEvents()
		}
	}
}

func (w *Watcher) processBufferedEvents() {
	w.bufferMu.Lock()
	defer w.bufferMu.Unlock()

	now := time.Now()
	eventsToEmit := make([]FileChangeEvent, 0)

	for key, timestamp := range w.eventBuffer {
		if now.Sub(timestamp) >= w.debounceDur {
			parts := splitLast(key, ":")
			if len(parts) == 2 {
				eventsToEmit = append(eventsToEmit, FileChangeEvent{
					Path:      parts[0],
					Operation: parts[1],
					Timestamp: timestamp,
				})
			}
			delete(w.eventBuffer, key)
		}
	}

	for _, event := range eventsToEmit {
		select {
		case w.eventChan <- event:
		default:
		}

		if w.onFileChange != nil {
			w.onFileChange(event)
		}
	}
}

func (w *Watcher) getOperationString(op fsnotify.Op) string {
	switch {
	case op&fsnotify.Create == fsnotify.Create:
		return "create"
	case op&fsnotify.Write == fsnotify.Write:
		return "write"
	case op&fsnotify.Remove == fsnotify.Remove:
		return "remove"
	case op&fsnotify.Rename == fsnotify.Rename:
		return "rename"
	case op&fsnotify.Chmod == fsnotify.Chmod:
		return "chmod"
	default:
		return ""
	}
}

func splitLast(s, sep string) []string {
	idx := -1
	for i := len(s) - 1; i >= 0; i-- {
		if len(sep) == 1 && s[i] == sep[0] {
			idx = i
			break
		}
	}
	if idx == -1 {
		return []string{s}
	}
	return []string{s[:idx], s[idx+1:]}
}

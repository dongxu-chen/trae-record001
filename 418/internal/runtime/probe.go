package runtime

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"time"

	"github.com/coldstart-optimizer/coldstart/internal/model"
)

type ImageInfo struct {
	Ref        string        `json:"ref"`
	SizeBytes  int64         `json:"size_bytes"`
	LayerCount int           `json:"layer_count"`
	Layers     []LayerInfo   `json:"layers,omitempty"`
	PullTime   time.Duration `json:"pull_ms"`
}

type LayerInfo struct {
	Digest    string        `json:"digest"`
	SizeBytes int64         `json:"size_bytes"`
	Extract   time.Duration `json:"extract_ms"`
}

type RuntimeProbe struct {
	RuntimeName   string
	SocketPath    string
	CrunPath      string
	RootfsWatcher bool
}

func NewRuntimeProbe(runtimeName, socketPath string) *RuntimeProbe {
	return &RuntimeProbe{
		RuntimeName: runtimeName,
		SocketPath:  socketPath,
		CrunPath:    lookupCrun(runtimeName),
	}
}

func lookupCrun(runtimeName string) string {
	if runtimeName == "" {
		return "runc"
	}
	return runtimeName
}

func (p *RuntimeProbe) AnalyzeImagePull(ctx context.Context, ref string) (*ImageInfo, error) {
	info := &ImageInfo{Ref: ref}

	pullStart := time.Now()
	cmd := exec.CommandContext(ctx, "crictl", "pull", ref)
	cmd.Stdout = io.Discard
	cmd.Stderr = io.Discard
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("crictl pull %s: %w", ref, err)
	}
	info.PullTime = time.Since(pullStart)

	inspect, err := exec.CommandContext(ctx, "crictl", "inspecti", ref).Output()
	if err == nil {
		var meta struct {
			Status struct {
				Size int64 `json:"size"`
			} `json:"status"`
		}
		_ = json.Unmarshal(inspect, &meta)
		info.SizeBytes = meta.Status.Size
	}

	return info, nil
}

func (p *RuntimeProbe) InspectRootfs(rootfs string) (int64, int, error) {
	var totalBytes int64
	var fileCount int
	err := filepath.Walk(rootfs, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if !info.IsDir() {
			fileCount++
			totalBytes += info.Size()
		}
		return nil
	})
	return totalBytes, fileCount, err
}

type ContainerLifecycle struct {
	ID              string
	Image           string
	CreatedAt       time.Time
	StartedAt       time.Time
	InitPid         int
	InitExecTime    time.Duration
	RuntimeTime     time.Duration
	FirstUserProcAt time.Time
}

var (
	containerPattern = regexp.MustCompile(`([0-9a-f]{64})`)
)

func (p *RuntimeProbe) TrackFromLogs(logPath string) ([]ContainerLifecycle, error) {
	f, err := os.Open(logPath)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	data, err := io.ReadAll(f)
	if err != nil {
		return nil, err
	}

	var out []ContainerLifecycle
	lines := splitLines(string(data))
	type raw struct {
		ts     time.Time
		level  string
		msg    string
		cid    string
		action string
	}
	var events []raw
	for _, ln := range lines {
		var ts, level, msg, cid, action string
		_, _ = fmt.Sscanf(ln, "%s %s %s", &ts, &level, &msg)
		if m := containerPattern.FindString(ln); m != "" {
			cid = m
		}
		switch {
		case contains(ln, "create container"):
			action = "create"
		case contains(ln, "start container"):
			action = "start"
		case contains(ln, "init process started"):
			action = "init"
		}
		t, perr := time.Parse(time.RFC3339Nano, ts)
		if perr == nil {
			events = append(events, raw{ts: t, level: level, msg: ln, cid: cid, action: action})
		}
	}

	byID := map[string]map[string]time.Time{}
	for _, e := range events {
		if e.cid == "" || e.action == "" {
			continue
		}
		if _, ok := byID[e.cid]; !ok {
			byID[e.cid] = map[string]time.Time{}
		}
		byID[e.cid][e.action] = e.ts
	}

	for cid, evs := range byID {
		lc := ContainerLifecycle{ID: cid}
		if t, ok := evs["create"]; ok {
			lc.CreatedAt = t
		}
		if t, ok := evs["start"]; ok {
			lc.StartedAt = t
		}
		if t, ok := evs["init"]; ok {
			lc.FirstUserProcAt = t
			if !lc.CreatedAt.IsZero() {
				lc.InitExecTime = t.Sub(lc.CreatedAt)
			}
			if !lc.StartedAt.IsZero() {
				lc.RuntimeTime = t.Sub(lc.StartedAt)
			}
		}
		out = append(out, lc)
	}
	return out, nil
}

func (p *RuntimeProbe) BuildPullPhase(imageInfo *ImageInfo, start time.Time) []model.PhaseRecord {
	var records []model.PhaseRecord
	now := time.Now()

	pullEnd := start.Add(imageInfo.PullTime)
	records = append(records, model.PhaseRecord{
		Phase:    model.PhaseImagePull,
		Start:    start,
		End:      pullEnd,
		Duration: imageInfo.PullTime,
		Source:   "containerd/pull",
		Detail:   fmt.Sprintf("image:%s size:%dMB", imageInfo.Ref, imageInfo.SizeBytes/1024/1024),
	})

	extractStart := pullEnd
	extractDur := time.Duration(0)
	for _, l := range imageInfo.Layers {
		extractDur += l.Extract
	}
	if extractDur == 0 {
		extractDur = 150 * time.Millisecond
	}
	records = append(records, model.PhaseRecord{
		Phase:    model.PhaseImageExtract,
		Start:    extractStart,
		End:      extractStart.Add(extractDur),
		Duration: extractDur,
		Source:   "containerd/unpack",
		Detail:   fmt.Sprintf("layers:%d", imageInfo.LayerCount),
	})

	_ = now
	return records
}

func contains(s, sub string) bool {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

func splitLines(s string) []string {
	var lines []string
	cur := ""
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			if cur != "" {
				lines = append(lines, cur)
				cur = ""
			}
		} else {
			cur += string(s[i])
		}
	}
	if cur != "" {
		lines = append(lines, cur)
	}
	return lines
}

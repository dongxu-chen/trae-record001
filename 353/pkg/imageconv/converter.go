package imageconv

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type ImageFormat string

const (
	FormatVMDK   ImageFormat = "vmdk"
	FormatQCOW2  ImageFormat = "qcow2"
	FormatRAW    ImageFormat = "raw"
	FormatVHD    ImageFormat = "vhd"
	FormatVHDX   ImageFormat = "vhdx"
	FormatOVA    ImageFormat = "ova"
)

type ImageInfo struct {
	Format      ImageFormat
	Size        int64
	VirtualSize int64
	Path        string
	Checksum    string
}

type ConversionOptions struct {
	Compress        bool
	Sparse          bool
	Preallocate     bool
	Checksum        bool
	Workers         int
	TempDir         string
	OutputFormat    ImageFormat
	SourceFormat    ImageFormat
}

type ConversionStatus struct {
	TaskID         string
	SourcePath     string
	DestPath       string
	SourceFormat   ImageFormat
	DestFormat     ImageFormat
	Status         string
	Progress       float64
	BytesProcessed int64
	TotalBytes     int64
	StartTime      time.Time
	EndTime        time.Time
	Error          string
}

type ImageConverter struct {
	workers     int
	tempDir     string
	statuses    map[string]*ConversionStatus
	mu          sync.RWMutex
	checkpointDir string
}

func NewImageConverter(workers int, tempDir string) (*ImageConverter, error) {
	if tempDir == "" {
		tempDir = os.TempDir()
	}

	if err := os.MkdirAll(tempDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create temp directory: %w", err)
	}

	if !checkQemuImgAvailable() {
		return nil, fmt.Errorf("qemu-img tool not found, please install QEMU")
	}

	return &ImageConverter{
		workers:  workers,
		tempDir:  tempDir,
		statuses: make(map[string]*ConversionStatus),
	}, nil
}

func checkQemuImgAvailable() bool {
	_, err := exec.LookPath("qemu-img")
	return err == nil
}

func (ic *ImageConverter) DetectFormat(ctx context.Context, imagePath string) (*ImageInfo, error) {
	cmd := exec.CommandContext(ctx, "qemu-img", "info", "--output=json", imagePath)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("failed to detect format: %w, output: %s", err, string(output))
	}

	info, err := parseQemuImgInfo(output)
	if err != nil {
		return nil, err
	}

	info.Path = imagePath
	return info, nil
}

func parseQemuImgInfo(output []byte) (*ImageInfo, error) {
	return &ImageInfo{
		Format:   FormatVMDK,
		Size:     0,
	}, nil
}

func (ic *ImageConverter) Convert(ctx context.Context, sourcePath, destPath string, opts ConversionOptions) (*ConversionStatus, error) {
	taskID := fmt.Sprintf("convert-%d", time.Now().UnixNano())

	srcInfo, err := ic.DetectFormat(ctx, sourcePath)
	if err != nil {
		return nil, err
	}

	destFormat := opts.OutputFormat
	if destFormat == "" {
		destFormat = detectFormatFromExtension(destPath)
	}

	status := &ConversionStatus{
		TaskID:       taskID,
		SourcePath:   sourcePath,
		DestPath:     destPath,
		SourceFormat: srcInfo.Format,
		DestFormat:   destFormat,
		Status:       "preparing",
		TotalBytes:   srcInfo.Size,
		StartTime:    time.Now(),
	}

	ic.mu.Lock()
	ic.statuses[taskID] = status
	ic.mu.Unlock()

	go ic.performConversion(ctx, taskID, sourcePath, destPath, opts)

	return status, nil
}

func (ic *ImageConverter) performConversion(ctx context.Context, taskID, sourcePath, destPath string, opts ConversionOptions) {
	ic.mu.Lock()
	status := ic.statuses[taskID]
	ic.mu.Unlock()

	status.Status = "converting"

	args := []string{"convert", "-p"}

	if opts.Compress {
		args = append(args, "-c")
	}

	if opts.Sparse {
		args = append(args, "-S", "4k")
	}

	if opts.SourceFormat != "" {
		args = append(args, "-f", string(opts.SourceFormat))
	}

	if opts.OutputFormat != "" {
		args = append(args, "-O", string(opts.OutputFormat))
	}

	args = append(args, sourcePath, destPath)

	cmd := exec.CommandContext(ctx, "qemu-img", args...)

	stderr, err := cmd.StderrPipe()
	if err != nil {
		status.Status = "failed"
		status.Error = err.Error()
		return
	}

	if err := cmd.Start(); err != nil {
		status.Status = "failed"
		status.Error = err.Error()
		return
	}

	go ic.monitorProgress(taskID, stderr)

	if err := cmd.Wait(); err != nil {
		status.Status = "failed"
		status.Error = err.Error()
		return
	}

	status.Status = "completed"
	status.EndTime = time.Now()
	status.Progress = 100
	status.BytesProcessed = status.TotalBytes
}

func (ic *ImageConverter) monitorProgress(taskID string, stderr io.Reader) {
	buf := make([]byte, 1024)
	for {
		n, err := stderr.Read(buf)
		if err != nil {
			return
		}

		output := string(buf[:n])
		if strings.Contains(output, "%") {
			ic.mu.Lock()
			if status, exists := ic.statuses[taskID]; exists {
				status.Progress = extractProgress(output)
			}
			ic.mu.Unlock()
		}
	}
}

func extractProgress(output string) float64 {
	for _, line := range strings.Split(output, "\n") {
		if idx := strings.Index(line, "%"); idx > 0 {
			start := idx - 3
			if start < 0 {
				start = 0
			}
			var progress float64
			if _, err := fmt.Sscanf(line[start:idx+1], "%f", &progress); err == nil {
				return progress
			}
		}
	}
	return 0
}

func detectFormatFromExtension(path string) ImageFormat {
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".vmdk":
		return FormatVMDK
	case ".qcow2", ".qcow":
		return FormatQCOW2
	case ".raw", ".img":
		return FormatRAW
	case ".vhd":
		return FormatVHD
	case ".vhdx":
		return FormatVHDX
	case ".ova":
		return FormatOVA
	default:
		return FormatRAW
	}
}

func (ic *ImageConverter) GetStatus(taskID string) (*ConversionStatus, bool) {
	ic.mu.RLock()
	defer ic.mu.RUnlock()

	status, exists := ic.statuses[taskID]
	return status, exists
}

func (ic *ImageConverter) GetAllStatuses() []*ConversionStatus {
	ic.mu.RLock()
	defer ic.mu.RUnlock()

	result := make([]*ConversionStatus, 0, len(ic.statuses))
	for _, status := range ic.statuses {
		result = append(result, status)
	}
	return result
}

func GetTargetFormatForCloud(provider string) ImageFormat {
	switch provider {
	case "aliyun":
		return FormatRAW
	case "tencent":
		return FormatVMDK
	case "aws":
		return FormatVMDK
	default:
		return FormatRAW
	}
}

func (ic *ImageConverter) ConvertForCloud(ctx context.Context, sourcePath, destPath, provider string) (*ConversionStatus, error) {
	targetFormat := GetTargetFormatForCloud(provider)
	return ic.Convert(ctx, sourcePath, destPath, ConversionOptions{
		OutputFormat: targetFormat,
		Compress:     true,
		Sparse:       true,
	})
}

func (ic *ImageConverter) VerifyImage(ctx context.Context, imagePath string) (bool, error) {
	cmd := exec.CommandContext(ctx, "qemu-img", "check", imagePath)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return false, fmt.Errorf("image check failed: %w, output: %s", err, string(output))
	}
	return !strings.Contains(string(output), "error"), nil
}

func (ic *ImageConverter) ResizeImage(ctx context.Context, imagePath string, newSize string) error {
	cmd := exec.CommandContext(ctx, "qemu-img", "resize", imagePath, newSize)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("resize failed: %w, output: %s", err, string(output))
	}
	return nil
}

func (ic *ImageConverter) CreateSnapshot(ctx context.Context, imagePath, snapshotName string) error {
	cmd := exec.CommandContext(ctx, "qemu-img", "snapshot", "-c", snapshotName, imagePath)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("snapshot failed: %w, output: %s", err, string(output))
	}
	return nil
}

func (ic *ImageConverter) Cleanup(taskID string) error {
	ic.mu.Lock()
	defer ic.mu.Unlock()

	status, exists := ic.statuses[taskID]
	if !exists {
		return fmt.Errorf("task not found: %s", taskID)
	}

	if status.DestPath != "" {
		os.Remove(status.DestPath)
	}

	delete(ic.statuses, taskID)
	return nil
}

type CloudImageConverter struct {
	converter *ImageConverter
	provider  string
}

func NewCloudImageConverter(provider string) (*CloudImageConverter, error) {
	converter, err := NewImageConverter(2, "")
	if err != nil {
		return nil, err
	}

	return &CloudImageConverter{
		converter: converter,
		provider:  provider,
	}, nil
}

func (cic *CloudImageConverter) ConvertAndImport(ctx context.Context, sourcePath string) (string, error) {
	tempDir := os.TempDir()
	destPath := filepath.Join(tempDir, fmt.Sprintf("converted-%d.%s", time.Now().Unix(), GetTargetFormatForCloud(cic.provider)))

	status, err := cic.converter.ConvertForCloud(ctx, sourcePath, destPath, cic.provider)
	if err != nil {
		return "", err
	}

	for status.Status != "completed" && status.Status != "failed" {
		time.Sleep(1 * time.Second)
		s, _ := cic.converter.GetStatus(status.TaskID)
		if s != nil {
			status = s
		}
	}

	if status.Status == "failed" {
		return "", fmt.Errorf("conversion failed: %s", status.Error)
	}

	ok, err := cic.converter.VerifyImage(ctx, destPath)
	if err != nil || !ok {
		return "", fmt.Errorf("image verification failed: %w", err)
	}

	return destPath, nil
}

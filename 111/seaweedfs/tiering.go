package seaweedfs

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"sort"
	"strings"
	"sync"
	"time"

	"cloud-storage-gateway/config"
	"cloud-storage-gateway/database"
	"cloud-storage-gateway/models"

	"github.com/minio/minio-go/v7"
)

type SmallFileManager struct {
	pendingFiles    map[string]*PendingFile
	pendingTotalSize int64
	mu              sync.Mutex
	flushTimer      *time.Timer
}

type PendingFile struct {
	FileID      string
	FileName    string
	Size        int64
	AddedAt     time.Time
	Metadata   interface{}
}

type MergeManifest struct {
	ManifestID  string           `json:"manifest_id"`
	TotalFiles  int              `json:"total_files"`
	TotalSize   int64            `json:"total_size"`
	CreatedAt    time.Time        `json:"created_at"`
	Files        []*FileManifestEntry `json:"files"`
}

type FileManifestEntry struct {
	FileID     string `json:"file_id"`
	FileName   string `json:"file_name"`
	Offset     int64  `json:"offset"`
	Size       int64  `json:"size"`
	Checksum   string `json:"checksum"`
}

const (
	DefaultMergeThresholdSize = 64 * 1024 * 1024
	DefaultMergeMaxFiles  = 1000
	DefaultMergeWaitTime  = 5 * time.Minute
)

var (
	SmallFileMgr *SmallFileManager
	tierOnce     sync.Once
)

func InitSmallFileManager() {
	tierOnce.Do(func() {
		SmallFileMgr = &SmallFileManager{
			pendingFiles:    make(map[string]*PendingFile),
			pendingTotalSize: 0,
		}

		SmallFileMgr.flushTimer = time.AfterFunc(DefaultMergeWaitTime, SmallFileMgr.autoFlush)
		log.Println("Small file merge manager initialized")
	})
}

func IsSmallFile(size int64) bool {
	return size < config.SmallFileThresholdSize
}

func (sfm *SmallFileManager) AddSmallFile(fileID, fileName string, size int64, metadata interface{}) {
	sfm.mu.Lock()
	defer sfm.mu.Unlock()

	sfm.pendingFiles[fileID] = &PendingFile{
		FileID:   fileID,
		FileName: fileName,
		Size:     size,
		AddedAt:  time.Now(),
		Metadata: metadata,
	}
	sfm.pendingTotalSize += size

	log.Printf("Added small file %s (size: %d) to merge queue, pending total: %d, queue size: %d",
		fileID, size, sfm.pendingTotalSize, len(sfm.pendingFiles))

	if sfm.shouldFlush() {
		go sfm.Flush()
	}
}

func (sfm *SmallFileManager) shouldFlush() bool {
	return sfm.pendingTotalSize >= config.SmallFileThresholdSize ||
		len(sfm.pendingFiles) >= config.SmallFileMaxFiles
}

func (sfm *SmallFileManager) autoFlush() {
	sfm.mu.Lock()
	if len(sfm.pendingFiles) > 0 {
		sfm.mu.Unlock()
		sfm.Flush()
	} else {
		sfm.mu.Unlock()
	}
	sfm.flushTimer.Reset(DefaultMergeWaitTime)
}

func (sfm *SmallFileManager) Flush() {
	sfm.mu.Lock()
	if len(sfm.pendingFiles) == 0 {
		sfm.mu.Unlock()
		return
	}

	pendingCopy := make(map[string]*PendingFile)
	for k, v := range sfm.pendingFiles {
		pendingCopy[k] = v
	}
	totalSize := sfm.pendingTotalSize
	sfm.pendingFiles = make(map[string]*PendingFile)
	sfm.pendingTotalSize = 0
	sfm.mu.Unlock()

	manifestID := fmt.Sprintf("merge-%d", time.Now().UnixNano())
	log.Printf("Starting merge %d files (%d bytes) into manifest %s",
		len(pendingCopy), totalSize, manifestID)

	if err := sfm.mergeFiles(manifestID, pendingCopy); err != nil {
		log.Printf("Merge failed: %v", err)
		sfm.mu.Lock()
		for fid, pf := range pendingCopy {
			sfm.pendingFiles[fid] = pf
		}
		sfm.pendingTotalSize += totalSize
		sfm.mu.Unlock()
		return
	}

	log.Printf("Successfully merged files into manifest %s", manifestID)
}

func (sfm *SmallFileManager) mergeFiles(manifestID string, files map[string]*PendingFile) error {
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)

	manifest := &MergeManifest{
		ManifestID: manifestID,
		TotalFiles:  len(files),
		TotalSize:   0,
		CreatedAt:    time.Now(),
		Files:        make([]*FileManifestEntry, 0, len(files)),
	}

	sortedFileIDs := make([]string, 0, len(files))
	for fid := range files {
		sortedFileIDs = append(sortedFileIDs, fid)
	}
	sort.Strings(sortedFileIDs)

	var currentOffset := int64(0)

	for _, fileID := range sortedFileIDs {
		pf := files[fileID]
		
		obj, err := SWClient.DownloadFileS3(context.Background(), fmt.Sprintf("files/%s", fileID))
		if err != nil {
			log.Printf("Failed to read file %s: %v", fileID, err)
			continue
		}

		fileData, err := io.ReadAll(obj)
		obj.Close()
		if err != nil {
			log.Printf("Failed to read file data %s: %v", fileID, err)
			continue
		}

		hdr := &tar.Header{
			Name: fileID,
			Mode: 0644,
			Size: int64(len(fileData)),
		}
		if err := tw.WriteHeader(hdr); err != nil {
			log.Printf("Failed to write tar header for %s: %v", fileID, err)
			continue
		}

		if _, err := tw.Write(fileData); err != nil {
			log.Printf("Failed to write tar data for %s: %v", fileID, err)
			continue
		}

		checksum := sha256.Sum256(fileData)
		manifest.Files = append(manifest.Files, &FileManifestEntry{
			FileID:   fileID,
			FileName: pf.FileName,
			Offset:   currentOffset,
			Size:     int64(len(fileData)),
			Checksum: hex.EncodeToString(checksum[:]),
		})

		manifest.TotalSize += int64(len(fileData))
		currentOffset += int64(len(fileData))
	}

	if err := tw.Close(); err != nil {
		return fmt.Errorf("failed to close tar writer: %w", err)
	}

	var compressedBuf, err := compressGzip(buf.Bytes())
	if err != nil {
		return fmt.Errorf("failed to compress: %w", err)
	}

	mergedObjectName := fmt.Sprintf("merged/%s.tar.gz", manifestID)
	_, err = SWClient.S3Client.PutObject(context.Background(), config.SeaweedFSBucketName,
		mergedObjectName, bytes.NewReader(compressedBuf), int64(len(compressedBuf)),
		minio.PutObjectOptions{
			ContentType: "application/gzip",
		})
	if err != nil {
		return fmt.Errorf("failed to upload merged file: %w", err)
	}

	manifestData, _ := json.Marshal(manifest)
	manifestObjectName := fmt.Sprintf("manifests/%s.json", manifestID)
	_, err = SWClient.S3Client.PutObject(context.Background(), config.SeaweedFSBucketName,
		manifestObjectName, bytes.NewReader(manifestData), int64(len(manifestData)),
		minio.PutObjectOptions{
			ContentType: "application/json",
		})
	if err != nil {
		return fmt.Errorf("failed to upload manifest: %w", err)
	}

	for _, entry := range manifest.Files {
		database.DB.Model(&models.FileMetadata{}).
			Where("file_id = ?", entry.FileID).
			Updates(map[string]interface{}{
				"merged_object_path": mergedObjectName,
				"merged_manifest_id": manifestID,
				"is_merged":       true,
			})
	}

	var objectNames []string
	for fileID := range files {
		objectNames = append(objectNames, fmt.Sprintf("files/%s", fileID))
	}
	SWClient.DeleteObjects(context.Background(), objectNames)

	return nil
}

func compressGzip(data []byte) ([]byte, error) {
	var buf bytes.Buffer
	gz := gzip.NewWriter(&buf)
	if _, err := gz.Write(data); err != nil {
		return nil, err
	}
	if err := gz.Close(); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func decompressGzip(data []byte) ([]byte, error) {
	buf := bytes.NewReader(data)
	gz, err := gzip.NewReader(buf)
	if err != nil {
		return nil, err
	}
	defer gz.Close()
	return io.ReadAll(gz)
}

func GetMergedFile(fileID, manifestID string) ([]byte, error) {
	manifestObjectName := fmt.Sprintf("manifests/%s.json", manifestID)
	obj, err := SWClient.S3Client.GetObject(context.Background(), config.SeaweedFSBucketName, manifestObjectName, minio.GetObjectOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get manifest: %w", err)
	}
	defer obj.Close()

	manifestData, err := io.ReadAll(obj)
	if err != nil {
		return nil, fmt.Errorf("failed to read manifest: %w", err)
	}

	var manifest MergeManifest
	if err := json.Unmarshal(manifestData, &manifest); err != nil {
		return nil, fmt.Errorf("failed to parse manifest: %w", err)
	}

	var entry *FileManifestEntry
	for _, e := range manifest.Files {
		if e.FileID == fileID {
			entry = e
			break
		}
	}
	if entry == nil {
		return nil, fmt.Errorf("file not found in manifest")
	}

	mergedObjectName := fmt.Sprintf("merged/%s.tar.gz", manifestID)
	mergedObj, err := SWClient.S3Client.GetObject(context.Background(), config.SeaweedFSBucketName, mergedObjectName, minio.GetObjectOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get merged file: %w", err)
	}
	defer mergedObj.Close()

	mergedData, err := io.ReadAll(mergedObj)
	if err != nil {
		return nil, fmt.Errorf("failed to read merged data: %w", err)
	}

	decompressed, err := decompressGzip(mergedData)
	if err != nil {
		return nil, fmt.Errorf("failed to decompress: %w", err)
	}

	tarReader := tar.NewReader(bytes.NewReader(decompressed))
	for {
		hdr, err := tarReader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("failed to read tar: %w", err)
		}
		if hdr.Name == fileID {
			fileData := make([]byte, hdr.Size)
			if _, err := io.ReadFull(tarReader, fileData); err != nil {
				return nil, fmt.Errorf("failed to read file from tar: %w", err)
			}
			return fileData, nil
		}
	}

	return nil, fmt.Errorf("file not found in tar archive")
}

func GetMergeStats() map[string]interface{} {
	SmallFileMgr.mu.Lock()
	defer SmallFileMgr.mu.Unlock()

	return map[string]interface{}{
		"pending_files_count": len(SmallFileMgr.pendingFiles),
		"pending_total_size":  SmallFileMgr.pendingTotalSize,
	}
}

func (sfm *SmallFileManager) Stop() {
	sfm.flushTimer.Stop()
	sfm.Flush()
	log.Println("Small file merge manager stopped")
}

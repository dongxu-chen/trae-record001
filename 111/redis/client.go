package redis

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"cloud-storage-gateway/config"

	"github.com/redis/go-redis/v9"
)

var Client *redis.Client

const (
	UploadSessionPrefix = "upload:session:"
	UploadChunkPrefix   = "upload:chunk:"
	FileMD5Prefix       = "file:md5:"
	SessionExpiration   = 24 * time.Hour
)

type UploadSession struct {
	FileID      string    `json:"file_id"`
	FileName    string    `json:"file_name"`
	FileSize    int64     `json:"file_size"`
	FileType    string    `json:"file_type"`
	TotalChunks int       `json:"total_chunks"`
	ChunkSize   int       `json:"chunk_size"`
	Status      string    `json:"status"`
	CreatedAt   time.Time `json:"created_at"`
}

type ChunkInfo struct {
	ChunkNumber int       `json:"chunk_number"`
	ChunkSize   int64     `json:"chunk_size"`
	ChunkPath   string    `json:"chunk_path"`
	UploadedAt  time.Time `json:"uploaded_at"`
}

func InitRedis() error {
	Client = redis.NewClient(&redis.Options{
		Addr:     config.RedisAddr,
		Password: config.RedisPassword,
		DB:       config.RedisDB,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := Client.Ping(ctx).Err(); err != nil {
		return fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return nil
}

func SaveUploadSession(ctx context.Context, session *UploadSession) error {
	data, err := json.Marshal(session)
	if err != nil {
		return err
	}
	key := UploadSessionPrefix + session.FileID
	return Client.Set(ctx, key, data, SessionExpiration).Err()
}

func GetUploadSession(ctx context.Context, fileID string) (*UploadSession, error) {
	key := UploadSessionPrefix + fileID
	data, err := Client.Get(ctx, key).Result()
	if err != nil {
		return nil, err
	}

	var session UploadSession
	if err := json.Unmarshal([]byte(data), &session); err != nil {
		return nil, err
	}
	return &session, nil
}

func DeleteUploadSession(ctx context.Context, fileID string) error {
	key := UploadSessionPrefix + fileID
	return Client.Del(ctx, key).Err()
}

func SaveChunkInfo(ctx context.Context, fileID string, chunk *ChunkInfo) error {
	data, err := json.Marshal(chunk)
	if err != nil {
		return err
	}
	key := fmt.Sprintf("%s%s:%d", UploadChunkPrefix, fileID, chunk.ChunkNumber)
	return Client.Set(ctx, key, data, SessionExpiration).Err()
}

func GetChunkInfo(ctx context.Context, fileID string, chunkNumber int) (*ChunkInfo, error) {
	key := fmt.Sprintf("%s%s:%d", UploadChunkPrefix, fileID, chunkNumber)
	data, err := Client.Get(ctx, key).Result()
	if err != nil {
		return nil, err
	}

	var chunk ChunkInfo
	if err := json.Unmarshal([]byte(data), &chunk); err != nil {
		return nil, err
	}
	return &chunk, nil
}

func IsChunkUploaded(ctx context.Context, fileID string, chunkNumber int) (bool, error) {
	key := fmt.Sprintf("%s%s:%d", UploadChunkPrefix, fileID, chunkNumber)
	exists, err := Client.Exists(ctx, key).Result()
	return exists > 0, err
}

func GetUploadedChunks(ctx context.Context, fileID string, totalChunks int) ([]ChunkInfo, error) {
	var chunks []ChunkInfo
	for i := 1; i <= totalChunks; i++ {
		chunk, err := GetChunkInfo(ctx, fileID, i)
		if err == nil {
			chunks = append(chunks, *chunk)
		}
	}
	return chunks, nil
}

func GetUploadedChunkNumbers(ctx context.Context, fileID string, totalChunks int) ([]int, error) {
	var numbers []int
	for i := 1; i <= totalChunks; i++ {
		uploaded, err := IsChunkUploaded(ctx, fileID, i)
		if err == nil && uploaded {
			numbers = append(numbers, i)
		}
	}
	return numbers, nil
}

func DeleteChunkInfos(ctx context.Context, fileID string, totalChunks int) error {
	var keys []string
	for i := 1; i <= totalChunks; i++ {
		keys = append(keys, fmt.Sprintf("%s%s:%d", UploadChunkPrefix, fileID, i))
	}
	if len(keys) > 0 {
		return Client.Del(ctx, keys...).Err()
	}
	return nil
}

func GetFileIDByMD5(ctx context.Context, md5 string) (string, error) {
	key := FileMD5Prefix + md5
	return Client.Get(ctx, key).Result()
}

func SaveFileMD5(ctx context.Context, md5 string, fileID string) error {
	key := FileMD5Prefix + md5
	return Client.Set(ctx, key, fileID, 0).Err()
}

func DeleteFileMD5(ctx context.Context, md5 string) error {
	key := FileMD5Prefix + md5
	return Client.Del(ctx, key).Err()
}

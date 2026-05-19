package seaweedfs

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"
	"time"

	"cloud-storage-gateway/config"
)

type ReplicationManager struct {
	PeerClusters   []*ReplicationPeer
	ReplicateQueue chan *ReplicationTask
	workerCount    int
	ctx            context.Context
	cancel         context.CancelFunc
}

type ReplicationPeer struct {
	Name       string
	MasterURL  string
	FilerURL   string
	S3Endpoint string
	AccessKey  string
	SecretKey  string
	IsActive   bool
}

type ReplicationTask struct {
	TaskID      string    `json:"task_id"`
	ObjectPath  string    `json:"object_path"`
	Operation   string    `json:"operation"`
	SourcePeer  string    `json:"source_peer"`
	TargetPeers []string  `json:"target_peers"`
	CreatedAt   time.Time `json:"created_at"`
	RetryCount  int       `json:"retry_count"`
}

type ReplicationStatus struct {
	TaskID      string    `json:"task_id"`
	ObjectPath  string    `json:"object_path"`
	Status      string    `json:"status"`
	TargetPeer  string    `json:"target_peer"`
	CompletedAt time.Time `json:"completed_at,omitempty"`
	Error       string    `json:"error,omitempty"`
}

var (
	ReplicationMgr *ReplicationManager
	replOnce       sync.Once
)

func InitReplication() {
	replOnce.Do(func() {
		ctx, cancel := context.WithCancel(context.Background())
		
		peers := make([]*ReplicationPeer, 0)
		for _, peerConfig := range config.ReplicationPeers {
			peers = append(peers, &ReplicationPeer{
				Name:       peerConfig.Name,
				MasterURL:  peerConfig.MasterURL,
				FilerURL:   peerConfig.FilerURL,
				S3Endpoint: peerConfig.S3Endpoint,
				AccessKey:  peerConfig.AccessKey,
				SecretKey:  peerConfig.SecretKey,
				IsActive:   true,
			})
		}

		ReplicationMgr = &ReplicationManager{
			PeerClusters:   peers,
			ReplicateQueue: make(chan *ReplicationTask, 1000),
			workerCount:    config.ReplicationWorkerCount,
			ctx:            ctx,
			cancel:         cancel,
		}

		for i := 0; i < ReplicationMgr.workerCount; i++ {
			go ReplicationMgr.replicationWorker(i)
		}

		log.Println("Cross-region replication initialized")
	})
}

func (rm *ReplicationManager) replicationWorker(workerID int) {
	log.Printf("Replication worker %d started", workerID)
	
	for {
		select {
		case <-rm.ctx.Done():
			log.Printf("Replication worker %d stopped", workerID)
			return
		case task := <-rm.ReplicateQueue:
			rm.processTask(task)
		}
	}
}

func (rm *ReplicationManager) processTask(task *ReplicationTask) {
	log.Printf("Processing replication task %s for %s", task.TaskID, task.ObjectPath)

	for _, targetPeer := range task.TargetPeers {
		peer := rm.getPeerByName(targetPeer)
		if peer == nil {
			log.Printf("Peer %s not found", targetPeer)
			continue
		}

		if err := rm.replicateToPeer(task, peer); err != nil {
			log.Printf("Failed to replicate to peer %s: %v", targetPeer, err)
			if task.RetryCount < config.ReplicationMaxRetries {
				task.RetryCount++
				go func(t *ReplicationTask) {
					time.Sleep(time.Duration(5*t.RetryCount) * time.Second)
					rm.ReplicateQueue <- t
				}(task)
			}
		} else {
			log.Printf("Successfully replicated %s to %s", task.ObjectPath, targetPeer)
		}
	}
}

func (rm *ReplicationManager) getPeerByName(name string) *ReplicationPeer {
	for _, peer := range rm.PeerClusters {
		if peer.Name == name {
			return peer
		}
	}
	return nil
}

func (rm *ReplicationManager) replicateToPeer(task *ReplicationTask, peer *ReplicationPeer) error {
	switch task.Operation {
	case "PUT":
		return rm.replicatePut(task, peer)
	case "DELETE":
		return rm.replicateDelete(task, peer)
	default:
		return fmt.Errorf("unknown operation: %s", task.Operation)
	}
}

func (rm *ReplicationManager) replicatePut(task *ReplicationTask, peer *ReplicationPeer) error {
	obj, err := SWClient.DownloadFileS3(context.Background(), task.ObjectPath)
	if err != nil {
		return fmt.Errorf("failed to read source object: %w", err)
	}
	defer obj.Close()

	stat, err := SWClient.StatObject(context.Background(), task.ObjectPath)
	if err != nil {
		return fmt.Errorf("failed to stat source object: %w", err)
	}

	targetURL := fmt.Sprintf("%s/%s/%s", peer.S3Endpoint, config.SeaweedFSBucketName, task.ObjectPath)
	
	buf := new(bytes.Buffer)
	if _, err := io.Copy(buf, obj); err != nil {
		return fmt.Errorf("failed to read object: %w", err)
	}

	req, err := http.NewRequest("PUT", targetURL, bytes.NewReader(buf.Bytes()))
	if err != nil {
		return err
	}
	req.ContentLength = stat.Size
	req.SetBasicAuth(peer.AccessKey, peer.SecretKey)

	client := &http.Client{Timeout: 5 * time.Minute}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("replication PUT failed with status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

func (rm *ReplicationManager) replicateDelete(task *ReplicationTask, peer *ReplicationPeer) error {
	targetURL := fmt.Sprintf("%s/%s/%s", peer.S3Endpoint, config.SeaweedFSBucketName, task.ObjectPath)
	
	req, err := http.NewRequest("DELETE", targetURL, nil)
	if err != nil {
		return err
	}
	req.SetBasicAuth(peer.AccessKey, peer.SecretKey)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("replication DELETE failed with status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

func (rm *ReplicationManager) SubmitReplicationTask(objectPath, operation string, targetPeers []string) string {
	taskID := fmt.Sprintf("repl-%d", time.Now().UnixNano())
	task := &ReplicationTask{
		TaskID:      taskID,
		ObjectPath:  objectPath,
		Operation:   operation,
		SourcePeer:  "local",
		TargetPeers: targetPeers,
		CreatedAt:   time.Now(),
		RetryCount:  0,
	}

	select {
	case rm.ReplicateQueue <- task:
		log.Printf("Replication task %s submitted for %s", taskID, objectPath)
	default:
		log.Printf("Replication queue full, dropping task for %s", objectPath)
	}

	return taskID
}

func (rm *ReplicationManager) GetAllPeers() []*ReplicationPeer {
	return rm.PeerClusters
}

func (rm *ReplicationManager) StopReplication() {
	rm.cancel()
	close(rm.ReplicateQueue)
	log.Println("Cross-region replication stopped")
}

func ReplicateToAllPeers(objectPath, operation string) {
	if ReplicationMgr == nil {
		return
	}

	peers := ReplicationMgr.GetAllPeers()
	peerNames := make([]string, 0, len(peers))
	for _, peer := range peers {
		peerNames = append(peerNames, peer.Name)
	}

	if len(peerNames) > 0 {
		ReplicationMgr.SubmitReplicationTask(objectPath, operation, peerNames)
	}
}

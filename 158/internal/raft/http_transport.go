package raft

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

type HTTPTransport struct {
	client    *http.Client
	peerAddrs map[string]string
	server    *http.Server
	mu        sync.RWMutex
	handler   *Node
}

func NewHTTPTransport(peerAddrs map[string]string) *HTTPTransport {
	return &HTTPTransport{
		client: &http.Client{
			Timeout: 500 * time.Millisecond,
			Transport: &http.Transport{
				MaxIdleConnsPerHost:   100,
				MaxConnsPerHost:     1000,
				IdleConnTimeout:     90 * time.Second,
				DisableCompression:  true,
			},
		},
		peerAddrs: peerAddrs,
	}
}

func (t *HTTPTransport) RequestVote(ctx context.Context, target string, req *VoteRequest) (*VoteResponse, error) {
	t.mu.RLock()
	addr, ok := t.peerAddrs[target]
	t.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unknown peer: %s", target)
	}

	url := fmt.Sprintf("http://%s/raft/vote", addr)
	return httpPost[VoteRequest, VoteResponse](ctx, t.client, url, req)
}

func (t *HTTPTransport) AppendEntries(ctx context.Context, target string, req *AppendEntriesRequest) (*AppendEntriesResponse, error) {
	t.mu.RLock()
	addr, ok := t.peerAddrs[target]
	t.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unknown peer: %s", target)
	}

	url := fmt.Sprintf("http://%s/raft/append", addr)
	return httpPost[AppendEntriesRequest, AppendEntriesResponse](ctx, t.client, url, req)
}

func (t *HTTPTransport) InstallSnapshot(ctx context.Context, target string, req *InstallSnapshotRequest) (*InstallSnapshotResponse, error) {
	t.mu.RLock()
	addr, ok := t.peerAddrs[target]
	t.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unknown peer: %s", target)
	}

	url := fmt.Sprintf("http://%s/raft/snapshot", addr)
	return httpPost[InstallSnapshotRequest, InstallSnapshotResponse](ctx, t.client, url, req)
}

func (t *HTTPTransport) Listen(addr string, handler *Node) error {
	t.mu.Lock()
	t.handler = handler
	t.mu.Unlock()

	mux := http.NewServeMux()
	
	mux.HandleFunc("/raft/vote", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var req VoteRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		resp, err := handler.HandleRequestVote(&req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	})

	mux.HandleFunc("/raft/append", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var req AppendEntriesRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		resp, err := handler.HandleAppendEntries(&req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	})

	mux.HandleFunc("/raft/state", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(handler.GetClusterState())
	})

	parts := strings.Split(addr, ":")
	port := parts[len(parts)-1]

	t.server = &http.Server{
		Addr:    ":" + port,
		Handler: mux,
	}

	log.Printf("Raft HTTP transport listening on %s", addr)
	return t.server.ListenAndServe()
}

func (t *HTTPTransport) Close() error {
	if t.server != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return t.server.Shutdown(ctx)
	}
	return nil
}

func httpPost[Req, Resp any](ctx context.Context, client *http.Client, url string, req *Req) (*Resp, error) {
	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, body)
	}

	var result Resp
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return &result, nil
}

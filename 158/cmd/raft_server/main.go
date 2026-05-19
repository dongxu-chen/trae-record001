package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"auction-platform/internal/auction"
	"auction-platform/internal/model"
	"auction-platform/internal/raft"
	"auction-platform/internal/redis"
)

type Config struct {
	NodeID     string            `json:"node_id"`
	NodeAddr   string            `json:"node_addr"`
	HTTPAddr   string            `json:"http_addr"`
	Region     string            `json:"region"`
	PeerAddrs  map[string]string `json:"peer_addrs"`
	DataDir    string            `json:"data_dir"`
	RedisAddr  string            `json:"redis_addr"`
}

type MultiRegionRouter struct {
	localRegion string
	regionNodes map[string][]string
	leaderCache string
	leaderExp   time.Time
	mu          sync.RWMutex
}

func NewMultiRegionRouter(localRegion string, regionNodes map[string][]string) *MultiRegionRouter {
	return &MultiRegionRouter{
		localRegion: localRegion,
		regionNodes: regionNodes,
	}
}

func (r *MultiRegionRouter) GetLeader() (string, error) {
	r.mu.RLock()
	if r.leaderCache != "" && time.Since(r.leaderExp) < 5*time.Second {
		defer r.mu.RUnlock()
		return r.leaderCache, nil
	}
	r.mu.RUnlock()

	r.mu.Lock()
	defer r.mu.Unlock()

	for region, nodes := range r.regionNodes {
		for _, node := range nodes {
			ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
			defer cancel()

			resp, err := http.Get(fmt.Sprintf("http://%s/raft/state", node))
			if err != nil {
				continue
			}
			defer resp.Body.Close()

			var state raft.ClusterState
			if err := json.NewDecoder(resp.Body).Decode(&state); err != nil {
				continue
			}

			if state.LeaderID != "" {
				r.leaderCache = state.LeaderID
				r.leaderExp = time.Now().Add(5 * time.Second)
				return state.LeaderID, nil
			}
		}
	}

	return "", fmt.Errorf("no leader found")
}

func (r *MultiRegionRouter) GetLocalNode() (string, bool) {
	nodes, ok := r.regionNodes[r.localRegion]
	if !ok || len(nodes) == 0 {
		return "", false
	}
	return nodes[0], true
}

var globalBidService *auction.BidService
var globalRouter *MultiRegionRouter

func main() {
	configPath := "config.json"
	if len(os.Args) > 1 {
		configPath = os.Args[1]
	}

	config, err := loadConfig(configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	err = redis.InitRedis(config.RedisAddr, nil, "", 0)
	if err != nil {
		log.Printf("Warning: Redis connection failed: %v", err)
	}

	raftConfig := &raft.RaftConfig{
		NodeID:     config.NodeID,
		NodeAddr:   config.NodeAddr,
		Region:     config.Region,
		PeerAddrs:  config.PeerAddrs,
		DataDir:    config.DataDir,
		HeartbeatInterval: 100 * time.Millisecond,
		ElectionTimeout:   300 * time.Millisecond,
	}

	service, err := auction.NewRaftBidService(raftConfig)
	if err != nil {
		log.Fatalf("Failed to create bid service: %v", err)
	}
	globalBidService = service

	if err := service.Start(); err != nil {
		log.Fatalf("Failed to start service: %v", err)
	}
	log.Printf("Raft node %s started in region %s", config.NodeID, config.Region)

	regionNodes := make(map[string][]string)
	regionNodes[config.Region] = []string{config.NodeAddr}
	globalRouter = NewMultiRegionRouter(config.Region, regionNodes)

	setupHTTPServer(config.HTTPAddr, service)

	log.Printf("HTTP server listening on %s", config.HTTPAddr)

	go setupDemoAuction(service)

	waitForShutdown(service)
}

func loadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, err
	}

	if config.HTTPAddr == "" {
		config.HTTPAddr = ":8080"
	}
	if config.RedisAddr == "" {
		config.RedisAddr = "localhost:6379"
	}
	if config.DataDir == "" {
		config.DataDir = "./data/" + config.NodeID
	}

	return &config, nil
}

func setupHTTPServer(addr string, service *auction.BidService) {
	mux := http.NewServeMux()

	mux.HandleFunc("/api/bid", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var cmd model.BidCommand
		if err := json.NewDecoder(r.Body).Decode(&cmd); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
		defer cancel()

		result, err := service.SubmitBid(ctx, &cmd)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(result)
	})

	mux.HandleFunc("/api/auctions", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(service.GetAllAuctions())
	})

	mux.HandleFunc("/api/auction/", func(w http.ResponseWriter, r *http.Request) {
		auctionID := r.URL.Path[len("/api/auction/"):]
		auction, ok := service.GetAuction(auctionID)
		if !ok {
			http.Error(w, "auction not found", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(auction)
	})

	mux.HandleFunc("/api/raft/state", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(service.RaftNode().GetClusterState())
	})

	mux.HandleFunc("/api/raft/leader", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"leader_id": service.RaftNode().LeaderID(),
			"is_leader": service.RaftNode().State() == raft.StateLeader,
			"term":      service.RaftNode().CurrentTerm(),
		})
	})

	mux.HandleFunc("/api/bids/history", func(w http.ResponseWriter, r *http.Request) {
		auctionID := r.URL.Query().Get("auction_id")
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(service.GetBidHistory(auctionID))
	})

	mux.HandleFunc("/api/proxy/bid", handleProxyBid)

	go func() {
		if err := http.ListenAndServe(addr, mux); err != nil {
			log.Fatalf("HTTP server failed: %v", err)
		}
	}()
}

func handleProxyBid(w http.ResponseWriter, r *http.Request) {
	var cmd model.BidCommand
	if err := json.NewDecoder(r.Body).Decode(&cmd); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if globalBidService.RaftNode().State() == raft.StateLeader {
		ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
		defer cancel()

		result, err := globalBidService.SubmitBid(ctx, &cmd)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(result)
		return
	}

	leaderID, err := globalRouter.GetLeader()
	if err != nil {
		http.Error(w, "no leader available", http.StatusServiceUnavailable)
		return
	}

	leaderAddr := globalBidService.RaftNode().Config.PeerAddrs[leaderID]
	if leaderAddr == "" {
		http.Error(w, "leader address not found", http.StatusServiceUnavailable)
		return
	}

	httpAddr := strings.Replace(leaderAddr, ":900", ":808", 1)
	proxyURL := fmt.Sprintf("http://%s/api/bid", httpAddr)

	body, _ := json.Marshal(cmd)
	resp, err := http.Post(proxyURL, "application/json", bytes.NewReader(body))
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	io.Copy(w, resp.Body)
}

func setupDemoAuction(service *auction.BidService) {
	time.Sleep(2 * time.Second)

	if service.RaftNode().State() != raft.StateLeader {
		log.Println("Not leader, skipping demo auction setup")
		return
	}

	cmd := &model.BidCommand{
		Type:      raft.CommandTypeCreateAuction,
		AuctionID: "demo_" + time.Now().Format("20060102150405"),
		UserID:    "system",
		Username:  "System",
		Price:     100.0,
		Timestamp: time.Now().Unix(),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	result, err := service.SubmitBid(ctx, cmd)
	if err != nil {
		log.Printf("Failed to create demo auction: %v", err)
	} else {
		log.Printf("Demo auction created: %v", result)
	}
}

func waitForShutdown(service *auction.BidService) {
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	<-sigCh

	log.Println("Shutting down...")

	if err := service.Stop(); err != nil {
		log.Printf("Error stopping service: %v", err)
	}

	log.Println("Shutdown complete")
}

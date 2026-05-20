package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"time"

	"auction-platform/internal/auction"
	"auction-platform/internal/model"
	"auction-platform/internal/redis"
	"auction-platform/internal/websocket"
)

func main() {
	shardAddrs := []string{}
	err := redis.InitRedis("localhost:6379", shardAddrs, "", 0)
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	log.Println("Connected to Redis successfully")

	auction.GlobalService.StartBidProcessor()
	auction.GlobalService.StartTimerBroadcast()

	setupDemoAuction()

	http.HandleFunc("/ws", handleWebSocket)
	http.HandleFunc("/api/auctions", handleGetAuctions)
	http.HandleFunc("/api/auction/", handleGetAuction)
	http.HandleFunc("/api/auction/create", handleCreateAuction)
	http.HandleFunc("/api/auction/hammer", handleHammerPrice)
	http.HandleFunc("/api/auction/conflicts", handleGetConflicts)
	http.HandleFunc("/api/arbitration/resolve", handleResolveConflict)
	http.HandleFunc("/api/arbitration/rollback", handleRollbackDeal)
	http.HandleFunc("/api/deals", handleGetDeals)
	http.HandleFunc("/api/bid", handleBid)
	http.HandleFunc("/api/bids/history", handleGetBidHistory)
	http.HandleFunc("/api/audit/logs", handleGetAuditLogs)
	http.HandleFunc("/api/user/balance", handleGetUserBalance)
	http.HandleFunc("/api/shard/stats", handleGetShardStats)
	http.Handle("/", http.FileServer(http.Dir("./static")))

	log.Println("Server starting on :8080...")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func setupDemoAuction() {
	product := &model.Product{
		ID:          "demo1",
		Name:        "iPhone 15 Pro Max",
		Description: "最新款苹果旗舰手机，256GB 深空黑色",
		StartPrice:  5000.0,
		IsHot:       true,
	}
	auction.GlobalService.CreateAuction(product, 5*time.Minute)
	log.Println("Demo auction created")
}

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
	clientID := r.URL.Query().Get("client_id")
	auctionID := r.URL.Query().Get("auction_id")

	if clientID == "" || auctionID == "" {
		http.Error(w, "Missing client_id or auction_id", http.StatusBadRequest)
		return
	}

	websocket.ServeWs(websocket.GlobalHub, w, r, clientID, auctionID, handleWebSocketMessage)
}

func handleWebSocketMessage(client *websocket.Client, rawMessage []byte) {
	var msg map[string]interface{}
	if err := json.Unmarshal(rawMessage, &msg); err != nil {
		log.Printf("Message parse error: %v", err)
		return
	}

	msgType, ok := msg["type"].(string)
	if !ok {
		return
	}

	switch msgType {
	case "bid":
		payload, ok := msg["payload"].(map[string]interface{})
		if !ok {
			return
		}

		auctionID, _ := payload["auction_id"].(string)
		userID, _ := payload["user_id"].(string)
		username, _ := payload["username"].(string)
		price, _ := payload["price"].(float64)
		budget, _ := payload["budget"].(float64)
		requestID, _ := payload["request_id"].(string)

		if budget == 0 {
			budget = 10000.0
		}

		bidReq := &model.UserBidRequest{
			AuctionID:   auctionID,
			UserID:      userID,
			Username:    username,
			Price:       price,
			Budget:      budget,
			RequestID:   requestID,
			Timestamp:   time.Now().Unix(),
			Millisecond: time.Now().UnixNano() / 1e6,
		}

		success, message, _ := auction.GlobalService.QueueBid(bidReq)

		result := map[string]interface{}{
			"success":    success,
			"message":    message,
			"request_id": requestID,
		}
		response := model.Message{
			Type:    model.MsgTypeBidResult,
			Payload: result,
		}
		data, _ := json.Marshal(response)
		client.Send <- data
	}
}

func handleGetAuctions(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	auctions := auction.GlobalService.GetAllAuctions()
	json.NewEncoder(w).Encode(auctions)
}

func handleGetAuction(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	auctionID := r.URL.Path[len("/api/auction/"):]
	auc, ok := auction.GlobalService.GetAuction(auctionID)
	if !ok {
		http.Error(w, "Auction not found", http.StatusNotFound)
		return
	}
	json.NewEncoder(w).Encode(auc)
}

func handleCreateAuction(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Name        string  `json:"name"`
		Description string  `json:"description"`
		StartPrice  float64 `json:"start_price"`
		Duration    int     `json:"duration"`
		IsHot       bool    `json:"is_hot"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	product := &model.Product{
		ID:          generateID(),
		Name:        req.Name,
		Description: req.Description,
		StartPrice:  req.StartPrice,
		IsHot:       req.IsHot,
	}

	auc := auction.GlobalService.CreateAuction(product, time.Duration(req.Duration)*time.Second)
	json.NewEncoder(w).Encode(auc)
}

func handleHammerPrice(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req model.HammerPriceRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	success, message := auction.GlobalService.HammerPrice(&req)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": success,
		"message": message,
	})
}

func handleGetConflicts(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	auctionID := r.URL.Query().Get("auction_id")
	conflicts, _ := auction.GlobalService.GetConflicts(auctionID)
	json.NewEncoder(w).Encode(conflicts)
}

func handleResolveConflict(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req model.ArbitrationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	success, message := auction.GlobalService.ResolveConflict(&req)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": success,
		"message": message,
	})
}

func handleRollbackDeal(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		DealID      string `json:"deal_id"`
		Reason      string `json:"reason"`
		ArbitratorID string `json:"arbitrator_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	success, message := auction.GlobalService.RollbackDeal(req.DealID, req.Reason, req.ArbitratorID)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": success,
		"message": message,
	})
}

func handleGetDeals(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	records, _ := auction.GlobalService.GetDealRecords(50)
	json.NewEncoder(w).Encode(records)
}

func handleBid(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var bidReq model.UserBidRequest
	if err := json.NewDecoder(r.Body).Decode(&bidReq); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if bidReq.RequestID == "" {
		bidReq.RequestID = generateID()
	}
	bidReq.Timestamp = time.Now().Unix()
	bidReq.Millisecond = time.Now().UnixNano() / 1e6
	if bidReq.Budget == 0 {
		bidReq.Budget = 10000.0
	}

	success, message, err := auction.GlobalService.QueueBid(&bidReq)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":    success,
		"message":    message,
		"request_id": bidReq.RequestID,
	})
}

func handleGetBidHistory(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	auctionID := r.URL.Query().Get("auction_id")
	limitStr := r.URL.Query().Get("limit")
	limit := int64(100)
	if limitStr != "" {
		if l, err := strconv.ParseInt(limitStr, 10, 64); err == nil {
			limit = l
		}
	}

	bids, _ := auction.GlobalService.GetBidHistory(auctionID, limit)
	json.NewEncoder(w).Encode(bids)
}

func handleGetAuditLogs(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	auctionID := r.URL.Query().Get("auction_id")
	limitStr := r.URL.Query().Get("limit")
	limit := int64(100)
	if limitStr != "" {
		if l, err := strconv.ParseInt(limitStr, 10, 64); err == nil {
			limit = l
		}
	}

	logs, _ := auction.GlobalService.GetAuditLogs(auctionID, limit)
	json.NewEncoder(w).Encode(logs)
}

func handleGetUserBalance(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		http.Error(w, "Missing user_id", http.StatusBadRequest)
		return
	}

	balance, err := auction.GlobalService.GetUserBalance(userID)
	if err != nil {
		balance = 10000.0
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"user_id": userID,
		"balance": balance,
	})
}

func handleGetShardStats(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	stats, _ := auction.GlobalService.GetShardStats()
	json.NewEncoder(w).Encode(stats)
}

func generateID() string {
	return time.Now().Format("20060102150405") + "-" + time.Now().Format(".000000000")
}

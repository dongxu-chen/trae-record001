package auction

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"auction-platform/internal/model"
	"auction-platform/internal/raft"
	"auction-platform/internal/redis"
)

type AuctionStateMachine struct {
	mu          sync.RWMutex
	auctions     map[string]*model.Auction
	bidHistory   map[string][]*model.Bid
	deals        map[string]*model.DealRecord
	applyIndex   uint64
}

func NewAuctionStateMachine() *AuctionStateMachine {
	return &AuctionStateMachine{
		auctions:   make(map[string]*model.Auction),
		bidHistory: make(map[string][]*model.Bid),
		deals:      make(map[string]*model.DealRecord),
	}
}

func (sm *AuctionStateMachine) Apply(entry *raft.LogEntry) (interface{}, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	cmdBytes, ok := entry.Command.([]byte)
	if !ok {
		jsonData, err := json.Marshal(entry.Command)
		if err != nil {
			return nil, err
		}
		cmdBytes = jsonData
	}

	var cmd model.BidCommand
	if err := json.Unmarshal(cmdBytes, &cmd); err != nil {
		return nil, err
	}

	var result interface{}
	var err error

	switch cmd.Type {
	case raft.CommandTypeBid:
		result, err = sm.applyBid(&cmd)
	case raft.CommandTypeCreateAuction:
		result, err = sm.applyCreateAuction(&cmd)
	case raft.CommandTypeConfirmDeal:
		result, err = sm.applyConfirmDeal(&cmd)
	case raft.CommandTypeRollback:
		result, err = sm.applyRollback(&cmd)
	default:
		err = fmt.Errorf("unknown command type: %s", cmd.Type)
	}

	if err == nil {
		sm.applyIndex = entry.Index
		go sm.cacheResult(entry.Index, &cmd, result)
	}

	return result, err
}

func (sm *AuctionStateMachine) applyBid(cmd *model.BidCommand) (interface{}, error) {
	auction, ok := sm.auctions[cmd.AuctionID]
	if !ok {
		return nil, fmt.Errorf("auction not found")
	}

	if auction.Status != "active" {
		return nil, fmt.Errorf("auction not active")
	}

	if cmd.Price <= auction.CurrentPrice {
		return nil, fmt.Errorf("bid price too low")
	}

	bid := &model.Bid{
		ID:        fmt.Sprintf("bid_%d_%s", time.Now().UnixNano(), cmd.UserID),
		AuctionID: cmd.AuctionID,
		UserID:    cmd.UserID,
		Username:  cmd.Username,
		Price:     cmd.Price,
		Timestamp: time.Now(),
	}

	auction.CurrentPrice = cmd.Price
	auction.HighestBid = bid
	auction.BidCount++

	sm.bidHistory[cmd.AuctionID] = append(sm.bidHistory[cmd.AuctionID], bid)

	return map[string]interface{}{
		"success":    true,
		"bid_id":      bid.ID,
		"price":       bid.Price,
		"timestamp":   bid.Timestamp,
	}, nil
}

func (sm *AuctionStateMachine) applyCreateAuction(cmd *model.BidCommand) (interface{}, error) {
	auction := &model.Auction{
		ID:           cmd.AuctionID,
		ProductID:    cmd.AuctionID,
		CurrentPrice: cmd.Price,
		StartTime:    time.Now(),
		Status:       "active",
		BidCount:     0,
	}

	sm.auctions[cmd.AuctionID] = auction
	sm.bidHistory[cmd.AuctionID] = make([]*model.Bid, 0)

	return map[string]interface{}{
		"success":   true,
		"auction_id": auction.ID,
	}, nil
}

func (sm *AuctionStateMachine) applyConfirmDeal(cmd *model.BidCommand) (interface{}, error) {
	auction, ok := sm.auctions[cmd.AuctionID]
	if !ok {
		return nil, fmt.Errorf("auction not found")
	}

	if auction.HighestBid == nil {
		return nil, fmt.Errorf("no bids for auction")
	}

	deal := &model.DealRecord{
		ID:          fmt.Sprintf("deal_%s", time.Now().Format("20060102150405")),
		AuctionID:   cmd.AuctionID,
		ProductID:   auction.ProductID,
		UserID:      auction.HighestBid.UserID,
		Username:    auction.HighestBid.Username,
		Price:       auction.HighestBid.Price,
		DealTime:    time.Now(),
	}

	sm.deals[deal.ID] = deal
	auction.Status = "confirmed"

	return map[string]interface{}{
		"success": true,
		"deal_id": deal.ID,
	}, nil
}

func (sm *AuctionStateMachine) applyRollback(cmd *model.BidCommand) (interface{}, error) {
	deal, ok := sm.deals[cmd.UserID]
	if !ok {
		return nil, fmt.Errorf("deal not found")
	}

	deal.IsRollback = true
	deal.RollbackReason = cmd.Username

	return map[string]interface{}{
		"success": true,
	}, nil
}

func (sm *AuctionStateMachine) cacheResult(index uint64, cmd *model.BidCommand, result interface{}) {
	ctx := context.Background()

	resultKey := fmt.Sprintf("apply_result:%d", index)
	resultData, _ := json.Marshal(result)
	redis.Client.Set(ctx, resultKey, string(resultData), 24*time.Hour)

	if cmd.Type == raft.CommandTypeBid {
		auctionKey := fmt.Sprintf("auction:%s", cmd.AuctionID)
		sm.mu.RLock()
		auction := sm.auctions[cmd.AuctionID]
		sm.mu.RUnlock()
		
		if auction != nil {
			auctionData, _ := json.Marshal(auction)
			redis.Client.Set(ctx, auctionKey, string(auctionData), 24*time.Hour)

			bidKey := fmt.Sprintf("current_bid:%s", cmd.AuctionID)
			bidData, _ := json.Marshal(auction.HighestBid)
			redis.Client.Set(ctx, bidKey, string(bidData), 24*time.Hour)
		}
	}
}

func (sm *AuctionStateMachine) Snapshot() ([]byte, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	snapshot := map[string]interface{}{
		"auctions":    sm.auctions,
		"bid_history":  sm.bidHistory,
		"deals":        sm.deals,
		"apply_index":  sm.applyIndex,
	}

	return json.Marshal(snapshot)
}

func (sm *AuctionStateMachine) Restore(snapshot []byte) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	var data map[string]json.RawMessage
	if err := json.Unmarshal(snapshot, &data); err != nil {
		return err
	}

	if err := json.Unmarshal(data["auctions"], &sm.auctions); err != nil {
		return err
	}
	if err := json.Unmarshal(data["bid_history"], &sm.bidHistory); err != nil {
		return err
	}
	if err := json.Unmarshal(data["deals"], &sm.deals); err != nil {
		return err
	}
	if err := json.Unmarshal(data["apply_index"], &sm.applyIndex); err != nil {
		return err
	}

	return nil
}

func (sm *AuctionStateMachine) GetAuction(auctionID string) (*model.Auction, bool) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	auction, ok := sm.auctions[auctionID]
	return auction, ok
}

func (sm *AuctionStateMachine) GetBidHistory(auctionID string) []*model.Bid {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.bidHistory[auctionID]
}

func (sm *AuctionStateMachine) GetDeal(dealID string) (*model.DealRecord, bool) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	deal, ok := sm.deals[dealID]
	return deal, ok
}

func (sm *AuctionStateMachine) GetAllAuctions() []*model.Auction {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	auctions := make([]*model.Auction, 0, len(sm.auctions))
	for _, auction := range sm.auctions {
		auctions = append(auctions, auction)
	}
	return auctions
}

func (sm *AuctionStateMachine) ApplyIndex() uint64 {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.applyIndex
}

type BidService struct {
	raftNode   *raft.Node
	stateMachine *AuctionStateMachine
	pendingCmds map[uint64]chan *applyResult
	mu           sync.RWMutex
}

type applyResult struct {
	result interface{}
	err    error
}

func NewBidService(raftNode *raft.Node, stateMachine *AuctionStateMachine) *BidService {
	s := &BidService{
		raftNode:    raftNode,
		stateMachine: stateMachine,
		pendingCmds:  make(map[uint64]chan *applyResult),
	}

	go s.watchApply()

	return s
}

func (s *BidService) watchApply() {
	for result := range s.raftNode.ApplyCh() {
		s.mu.Lock()
		ch, ok := s.pendingCmds[result.Index]
		if ok {
			delete(s.pendingCmds, result.Index)
			ch <- &applyResult{result: result.Result, err: result.Error}
			close(ch)
		}
		s.mu.Unlock()
	}
}

func (s *BidService) SubmitBid(ctx context.Context, cmd *model.BidCommand) (interface{}, error) {
	if s.raftNode.State() != raft.StateLeader {
		return nil, fmt.Errorf("not leader, leader is %s", s.raftNode.LeaderID())
	}

	cmdBytes, err := json.Marshal(cmd)
	if err != nil {
		return nil, err
	}

	index, err := s.raftNode.SubmitCommand(cmdBytes)
	if err != nil {
		return nil, err
	}

	resultCh := make(chan *applyResult, 1)
	s.mu.Lock()
	s.pendingCmds[index] = resultCh
	s.mu.Unlock()

	select {
	case result := <-resultCh:
		return result.result, result.err
	case <-ctx.Done():
		s.mu.Lock()
		delete(s.pendingCmds, index)
		s.mu.Unlock()
		return nil, ctx.Err()
	case <-time.After(3 * time.Second):
		s.mu.Lock()
		delete(s.pendingCmds, index)
		s.mu.Unlock()
		return nil, fmt.Errorf("timeout waiting for bid to be applied")
	}
}

func (s *BidService) GetAuction(auctionID string) (*model.Auction, bool) {
	return s.stateMachine.GetAuction(auctionID)
}

func (s *BidService) GetAllAuctions() []*model.Auction {
	return s.stateMachine.GetAllAuctions()
}

func (s *BidService) GetBidHistory(auctionID string) []*model.Bid {
	return s.stateMachine.GetBidHistory(auctionID)
}

func (s *BidService) RaftNode() *raft.Node {
	return s.raftNode
}

func (s *BidService) Start() error {
	return s.raftNode.Start()
}

func (s *BidService) Stop() error {
	return s.raftNode.Stop()
}

func NewRaftBidService(config *raft.RaftConfig) (*BidService, error) {
	stateMachine := NewAuctionStateMachine()
	
	transport := raft.NewHTTPTransport(config.PeerAddrs)
	
	node, err := raft.NewNode(config, stateMachine, transport)
	if err != nil {
		return nil, err
	}
	
	return NewBidService(node, stateMachine), nil
}

func StartRaftCluster(nodeConfigs []*raft.RaftConfig) ([]*BidService, error) {
	services := make([]*BidService, 0, len(nodeConfigs))
	
	for _, config := range nodeConfigs {
		service, err := NewRaftBidService(config)
		if err != nil {
			return nil, err
		}
		services = append(services, service)
	}
	
	for _, service := range services {
		if err := service.Start(); err != nil {
			log.Printf("Failed to start node: %v", err)
		}
	}
	
	time.Sleep(500 * time.Millisecond)
	
	return services, nil
}

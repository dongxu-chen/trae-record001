package auction

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"auction-platform/internal/model"
	"auction-platform/internal/redis"
	"auction-platform/internal/websocket"
)

const (
	AuctionStatusActive   = "active"
	AuctionStatusEnded    = "ended"
	AuctionStatusConfirmed = "confirmed"
	BidQueueKey          = "bid_queue"
	AuctionKeyPrefix     = "auction:"
	BidHistoryKeyPrefix   = "bid_history:"
	DealRecordKeyPrefix   = "deal_record:"
	DealRecordsListKey    = "deal_records"
)

type Service struct {
	mu           sync.RWMutex
	auctions     map[string]*model.Auction
	timers       map[string]*time.Timer
	ctx          context.Context
	cancel       context.CancelFunc
}

var GlobalService *Service

func NewService() *Service {
	ctx, cancel := context.WithCancel(context.Background())
	return &Service{
		auctions: make(map[string]*model.Auction),
		timers:   make(map[string]*time.Timer),
		ctx:      ctx,
		cancel:   cancel,
	}
}

func (s *Service) StartBidProcessor() {
	log.Println("Starting bid processor...")
	go s.processBidQueue()
}

func (s *Service) processBidQueue() {
	ticker := time.NewTicker(10 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-s.ctx.Done():
			return
		case <-ticker.C:
			for {
				var bidRequest model.UserBidRequest
				err := redis.RPop(s.ctx, BidQueueKey, &bidRequest)
				if err != nil {
					break
				}
				s.processBid(&bidRequest)
			}
		}
	}
}

func (s *Service) QueueBid(bidReq *model.UserBidRequest) (bool, string, error) {
	s.mu.RLock()
	auction, ok := s.auctions[bidReq.AuctionID]
	s.mu.RUnlock()

	if !ok {
		return false, "拍卖不存在", nil
	}

	if auction.Status != AuctionStatusActive {
		return false, "拍卖已结束", nil
	}

	currentTime := time.Now().Unix()
	auctionEndTime := auction.EndTime.Unix()

	if currentTime >= auctionEndTime {
		canEnd, err := redis.CheckAndSetAuctionEndLock(s.ctx, bidReq.AuctionID, currentTime, auctionEndTime)
		if err != nil {
			log.Printf("Check auction end lock error: %v", err)
		}
		if canEnd {
			go s.endAuction(bidReq.AuctionID)
		}
		return false, "拍卖已超时结束", nil
	}

	if bidReq.Price <= auction.CurrentPrice {
		return false, fmt.Sprintf("出价必须高于当前价格 %.2f", auction.CurrentPrice), nil
	}

	budgetCheckResult, err := redis.CheckUserBudgetAndReserve(
		s.ctx, bidReq.UserID, bidReq.AuctionID, bidReq.Price, bidReq.Budget, bidReq.RequestID)
	if err != nil {
		log.Printf("Budget check error: %v", err)
		return false, "系统错误，请重试", err
	}

	switch budgetCheckResult {
	case -1:
		return false, "用户预算不足，无法出价", nil
	case 0:
		return false, "重复的出价请求", nil
	case -2:
		return false, "预算校验失败", nil
	}

	enqueued, err := redis.EnqueueBidAtomically(s.ctx, BidQueueKey, bidReq, bidReq.RequestID)
	if err != nil {
		log.Printf("Enqueue bid error: %v", err)
		return false, "出价队列错误", err
	}

	if !enqueued {
		return false, "出价请求已存在，请勿重复提交", nil
	}

	return true, "出价已提交处理中", nil
}

func (s *Service) processBid(bidReq *model.UserBidRequest) {
	s.mu.Lock()
	auction, ok := s.auctions[bidReq.AuctionID]
	s.mu.Unlock()

	if !ok {
		log.Printf("Auction %s not found", bidReq.AuctionID)
		return
	}

	if auction.Status != AuctionStatusActive {
		log.Printf("Auction %s is not active", bidReq.AuctionID)
		redis.RefundUserBalance(s.ctx, bidReq.UserID, bidReq.Price)
		return
	}

	if bidReq.Price <= auction.CurrentPrice {
		log.Printf("Bid price %.2f is not higher than current price %.2f", bidReq.Price, auction.CurrentPrice)
		redis.RefundUserBalance(s.ctx, bidReq.UserID, bidReq.Price)
		return
	}

	now := time.Now()
	msTimestamp := now.UnixNano() / 1e6

	bid := &model.Bid{
		ID:          generateID(),
		AuctionID:   bidReq.AuctionID,
		UserID:      bidReq.UserID,
		Username:    bidReq.Username,
		Price:       bidReq.Price,
		Timestamp:   now,
		Millisecond: msTimestamp,
	}

	hasConflict, err := redis.DetectBidConflict(s.ctx, bidReq.AuctionID, msTimestamp, bid)
	if err != nil {
		log.Printf("Conflict detection error: %v", err)
	}

	if hasConflict {
		s.mu.Lock()
		auction.HasConflict = true
		s.mu.Unlock()
		log.Printf("Conflict detected for auction %s at ms %d", bidReq.AuctionID, msTimestamp)
	}

	s.mu.Lock()
	if auction.HighestBid != nil {
		redis.RefundUserBalance(s.ctx, auction.HighestBid.UserID, auction.HighestBid.Price)
	}
	auction.CurrentPrice = bidReq.Price
	auction.HighestBid = bid
	auction.BidCount++
	s.mu.Unlock()

	auctionKey := fmt.Sprintf("%s%s", AuctionKeyPrefix, bidReq.AuctionID)
	redis.Set(s.ctx, auctionKey, auction, 24*time.Hour)

	historyKey := fmt.Sprintf("%s%s", BidHistoryKeyPrefix, bidReq.AuctionID)
	redis.LPush(s.ctx, historyKey, bid)

	s.saveAuditLog(bidReq.AuctionID, bidReq.UserID, bidReq.Username, "BID_PLACED", "", fmt.Sprintf("Price: %.2f", bidReq.Price))

	log.Printf("Bid accepted: user=%s, price=%.2f, auction=%s", bidReq.Username, bidReq.Price, bidReq.AuctionID)

	s.broadcastBidUpdate(bidReq.AuctionID, bid)
}

func (s *Service) broadcastBidUpdate(auctionID string, bid *model.Bid) {
	msg := model.Message{
		Type:    model.MsgTypeBid,
		Payload: bid,
	}
	websocket.GlobalHub.BroadcastMessageToAuction(auctionID, msg)
}

func (s *Service) CreateAuction(product *model.Product, duration time.Duration) *model.Auction {
	auction := &model.Auction{
		ID:           generateID(),
		ProductID:     product.ID,
		Product:      product,
		CurrentPrice: product.StartPrice,
		StartTime:    time.Now(),
		EndTime:      time.Now().Add(duration),
		Status:       AuctionStatusActive,
		BidCount:     0,
		IsConfirmed:  false,
		HasConflict:  false,
	}

	if product.IsHot {
		auction.ShardKey = product.ID
	}

	s.mu.Lock()
	s.auctions[auction.ID] = auction
	s.mu.Unlock()

	auctionKey := fmt.Sprintf("%s%s", AuctionKeyPrefix, auction.ID)
	redis.Set(s.ctx, auctionKey, auction, 24*time.Hour)

	s.startAuctionTimer(auction.ID, auction.EndTime)

	s.saveAuditLog(auction.ID, "system", "system", "AUCTION_CREATED", "", fmt.Sprintf("Product: %s, Duration: %v", product.Name, duration))

	log.Printf("Auction created: %s, product: %s, duration: %v", auction.ID, product.Name, duration)
	return auction
}

func (s *Service) startAuctionTimer(auctionID string, endTime time.Time) {
	duration := time.Until(endTime)
	if duration <= 0 {
		s.endAuction(auctionID)
		return
	}

	timer := time.AfterFunc(duration, func() {
		canEnd, err := redis.CheckAndSetAuctionEndLock(
			s.ctx,
			auctionID,
			time.Now().Unix(),
			endTime.Unix(),
		)
		if err != nil {
			log.Printf("Check auction end lock error: %v", err)
		}
		if canEnd {
			s.endAuction(auctionID)
		}
	})

	s.mu.Lock()
	s.timers[auctionID] = timer
	s.mu.Unlock()
}

func (s *Service) endAuction(auctionID string) {
	s.mu.Lock()
	auction, ok := s.auctions[auctionID]
	if !ok {
		s.mu.Unlock()
		return
	}
	auction.Status = AuctionStatusEnded
	s.mu.Unlock()

	auctionKey := fmt.Sprintf("%s%s", AuctionKeyPrefix, auctionID)
	redis.Set(s.ctx, auctionKey, auction, 24*time.Hour)

	var dealRecord *model.DealRecord
	if auction.HighestBid != nil {
		dealRecord = &model.DealRecord{
			ID:          generateID(),
			AuctionID:   auction.ID,
			ProductID:   auction.ProductID,
			ProductName: auction.Product.Name,
			UserID:      auction.HighestBid.UserID,
			Username:    auction.HighestBid.Username,
			Price:       auction.HighestBid.Price,
			DealTime:    time.Now(),
			IsRollback:  false,
		}

		dealKey := fmt.Sprintf("%s%s", DealRecordKeyPrefix, dealRecord.ID)
		redis.Set(s.ctx, dealKey, dealRecord, 7*24*time.Hour)
		redis.LPush(s.ctx, DealRecordsListKey, dealRecord)

		s.saveAuditLog(auctionID, "system", "system", "AUCTION_ENDED", "", fmt.Sprintf("Winner: %s, Price: %.2f", dealRecord.Username, dealRecord.Price))

		log.Printf("Auction %s ended. Deal: user=%s, price=%.2f", auctionID, dealRecord.Username, dealRecord.Price)
	} else {
		log.Printf("Auction %s ended with no bids", auctionID)
	}

	endMsg := model.Message{
		Type:    model.MsgTypeAuctionEnd,
		Payload: map[string]interface{}{"auction_id": auctionID, "deal": dealRecord},
	}
	websocket.GlobalHub.BroadcastMessageToAuction(auctionID, endMsg)

	s.mu.Lock()
	if timer, exists := s.timers[auctionID]; exists {
		timer.Stop()
		delete(s.timers, auctionID)
	}
	s.mu.Unlock()
}

func (s *Service) HammerPrice(req *model.HammerPriceRequest) (bool, string) {
	s.mu.Lock()
	auction, ok := s.auctions[req.AuctionID]
	if !ok {
		s.mu.Unlock()
		return false, "拍卖不存在"
	}

	if auction.IsConfirmed {
		s.mu.Unlock()
		return false, "拍卖已确认"
	}

	if auction.HighestBid == nil {
		s.mu.Unlock()
		return false, "没有出价记录"
	}

	if auction.HighestBid.ID != req.BidID && req.BidID != "" {
		s.mu.Unlock()
		return false, "指定的出价不是最高价"
	}

	auction.IsConfirmed = true
	auction.Status = AuctionStatusConfirmed
	winningBid := auction.HighestBid
	s.mu.Unlock()

	redis.RecordHammerPrice(s.ctx, req.AuctionID, winningBid.ID, req.AuctioneerID, winningBid.Price, req.Remark)

	s.saveAuditLog(req.AuctionID, req.AuctioneerID, "auctioneer", "HAMMER_PRICE", "", fmt.Sprintf("Price: %.2f, Remark: %s", winningBid.Price, req.Remark))

	dealRecord := &model.DealRecord{
		ID:          generateID(),
		AuctionID:   auction.ID,
		ProductID:   auction.ProductID,
		ProductName: auction.Product.Name,
		UserID:      winningBid.UserID,
		Username:    winningBid.Username,
		Price:       winningBid.Price,
		DealTime:    time.Now(),
		IsRollback:  false,
	}

	dealKey := fmt.Sprintf("%s%s", DealRecordKeyPrefix, dealRecord.ID)
	redis.Set(s.ctx, dealKey, dealRecord, 7*24*time.Hour)
	redis.LPush(s.ctx, DealRecordsListKey, dealRecord)

	msg := model.Message{
		Type: model.MsgTypeAuctioneer,
		Payload: map[string]interface{}{
			"auction_id": req.AuctionID,
			"confirmed":  true,
			"winner":     winningBid,
			"remark":     req.Remark,
		},
	}
	websocket.GlobalHub.BroadcastMessageToAuction(req.AuctionID, msg)

	log.Printf("Hammer price confirmed for auction %s by auctioneer %s", req.AuctionID, req.AuctioneerID)
	return true, "成交确认成功"
}

func (s *Service) ResolveConflict(req *model.ArbitrationRequest) (bool, string) {
	err := redis.ResolveConflict(s.ctx, req.ConflictID, req.WinnerBidID, req.ArbitratorID, req.Reason)
	if err != nil {
		log.Printf("Resolve conflict error: %v", err)
		return false, "冲突解决失败"
	}

	s.saveAuditLog("", req.ArbitratorID, "arbitrator", "CONFLICT_RESOLVED", req.ConflictID, req.Reason)

	msg := model.Message{
		Type: model.MsgTypeArbitration,
		Payload: map[string]interface{}{
			"conflict_id":   req.ConflictID,
			"winner_bid_id": req.WinnerBidID,
			"reason":        req.Reason,
		},
	}
	websocket.GlobalHub.BroadcastMessage(msg)

	return true, "冲突解决成功"
}

func (s *Service) RollbackDeal(dealRecordID string, reason string, arbitratorID string) (bool, string) {
	err := redis.RollbackDeal(s.ctx, dealRecordID, reason, arbitratorID)
	if err != nil {
		log.Printf("Rollback deal error: %v", err)
		return false, "回滚失败"
	}

	s.saveAuditLog("", arbitratorID, "arbitrator", "DEAL_ROLLBACK", dealRecordID, reason)

	return true, "成交回滚成功"
}

func (s *Service) GetAuction(auctionID string) (*model.Auction, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	auction, ok := s.auctions[auctionID]
	return auction, ok
}

func (s *Service) GetAllAuctions() []*model.Auction {
	s.mu.RLock()
	defer s.mu.RUnlock()
	auctions := make([]*model.Auction, 0, len(s.auctions))
	for _, auction := range s.auctions {
		auctions = append(auctions, auction)
	}
	return auctions
}

func (s *Service) GetBidHistory(auctionID string, limit int64) ([]*model.Bid, error) {
	return redis.GetBidsSortedByTime(s.ctx, auctionID)
}

func (s *Service) GetDealRecords(limit int64) ([]*model.DealRecord, error) {
	results, err := redis.LRange(s.ctx, DealRecordsListKey, 0, limit-1)
	if err != nil {
		return nil, err
	}

	records := make([]*model.DealRecord, 0, len(results))
	for _, result := range results {
		var record model.DealRecord
		if err := json.Unmarshal([]byte(result), &record); err == nil {
			records = append(records, &record)
		}
	}
	return records, nil
}

func (s *Service) GetTimerInfo(auctionID string) *model.TimerInfo {
	s.mu.RLock()
	auction, ok := s.auctions[auctionID]
	s.mu.RUnlock()

	if !ok {
		return &model.TimerInfo{
			AuctionID:  auctionID,
			Remaining:  0,
			IsExpired:  true,
			ServerTime: time.Now().Unix(),
		}
	}

	remaining := time.Until(auction.EndTime)
	if remaining < 0 {
		remaining = 0
	}

	return &model.TimerInfo{
		AuctionID:  auctionID,
		Remaining:  int64(remaining.Seconds()),
		EndTime:    auction.EndTime.Unix(),
		IsExpired:  remaining <= 0,
		ServerTime: time.Now().Unix(),
	}
}

func (s *Service) StartTimerBroadcast() {
	log.Println("Starting timer broadcast...")
	ticker := time.NewTicker(500 * time.Millisecond)
	go func() {
		for {
			select {
			case <-s.ctx.Done():
				ticker.Stop()
				return
			case <-ticker.C:
				s.mu.RLock()
				for auctionID := range s.auctions {
					timerInfo := s.GetTimerInfo(auctionID)
					msg := model.Message{
						Type:    model.MsgTypeTimer,
						Payload: timerInfo,
					}
					websocket.GlobalHub.BroadcastMessageToAuction(auctionID, msg)
				}
				s.mu.RUnlock()
			}
		}
	}()
}

func (s *Service) GetUserBalance(userID string) (float64, error) {
	balance, err := redis.GetUserBalance(s.ctx, userID)
	if err != nil && err.Error() == "redis: nil" {
		return 10000.0, nil
	}
	return balance, err
}

func (s *Service) SetUserBalance(userID string, balance float64) error {
	return redis.SetUserBalance(s.ctx, userID, balance)
}

func (s *Service) GetConflicts(auctionID string) ([]*model.BidConflict, error) {
	return redis.GetConflicts(s.ctx, auctionID)
}

func (s *Service) GetAuditLogs(auctionID string, limit int64) ([]*model.AuditLog, error) {
	return redis.GetAuditLogs(s.ctx, auctionID, limit)
}

func (s *Service) saveAuditLog(auctionID string, operatorID string, operatorName string, action string, beforeData string, afterData string) {
	log := &model.AuditLog{
		ID:           generateID(),
		AuctionID:    auctionID,
		OperatorID:   operatorID,
		OperatorName: operatorName,
		Action:       action,
		BeforeData:   beforeData,
		AfterData:    afterData,
		Timestamp:    time.Now(),
	}
	redis.SaveAuditLog(s.ctx, log)
}

func (s *Service) GetShardStats() ([]*model.ShardStats, error) {
	return redis.GetShardStats(s.ctx)
}

func generateID() string {
	return fmt.Sprintf("%d", time.Now().UnixNano())
}

func init() {
	GlobalService = NewService()
}

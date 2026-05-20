package model

import "time"

type MessageType string

const (
	MsgTypeBid         MessageType = "bid"
	MsgTypeTimer       MessageType = "timer"
	MsgTypeAuctionEnd  MessageType = "auction_end"
	MsgTypeJoin        MessageType = "join"
	MsgTypeBidResult   MessageType = "bid_result"
	MsgTypeHistory     MessageType = "history"
	MsgTypeServerTime  MessageType = "server_time"
	MsgTypeAuctioneer  MessageType = "auctioneer"
	MsgTypeArbitration MessageType = "arbitration"
	MsgTypePlayback    MessageType = "playback"
)

type Message struct {
	Type    MessageType `json:"type"`
	Payload interface{} `json:"payload"`
}

type User struct {
	ID       string  `json:"id"`
	Username string  `json:"username"`
	Balance  float64 `json:"balance"`
	Role     string  `json:"role"`
}

type UserBidRequest struct {
	AuctionID   string  `json:"auction_id"`
	UserID      string  `json:"user_id"`
	Username    string  `json:"username"`
	Price       float64 `json:"price"`
	Budget      float64 `json:"budget"`
	RequestID   string  `json:"request_id"`
	Timestamp   int64   `json:"timestamp"`
	Millisecond int64   `json:"millisecond"`
}

type Product struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	StartPrice  float64   `json:"start_price"`
	ImageURL    string    `json:"image_url"`
	StartTime   time.Time `json:"start_time"`
	EndTime     time.Time `json:"end_time"`
	IsHot       bool      `json:"is_hot"`
	ShardKey    string    `json:"shard_key"`
}

type Bid struct {
	ID          string    `json:"id"`
	AuctionID   string    `json:"auction_id"`
	UserID      string    `json:"user_id"`
	Username    string    `json:"username"`
	Price       float64   `json:"price"`
	Timestamp   time.Time `json:"timestamp"`
	ShardKey    string    `json:"shard_key"`
	Millisecond int64     `json:"millisecond"`
}

type Auction struct {
	ID           string    `json:"id"`
	ProductID    string    `json:"product_id"`
	Product      *Product  `json:"product"`
	CurrentPrice float64   `json:"current_price"`
	HighestBid   *Bid      `json:"highest_bid"`
	StartTime    time.Time `json:"start_time"`
	EndTime      time.Time `json:"end_time"`
	Status       string    `json:"status"`
	BidCount     int       `json:"bid_count"`
	ShardKey     string    `json:"shard_key"`
	AuctioneerID string    `json:"auctioneer_id"`
	IsConfirmed  bool      `json:"is_confirmed"`
	HasConflict  bool      `json:"has_conflict"`
}

type DealRecord struct {
	ID             string    `json:"id"`
	AuctionID      string    `json:"auction_id"`
	ProductID      string    `json:"product_id"`
	ProductName    string    `json:"product_name"`
	UserID         string    `json:"user_id"`
	Username       string    `json:"username"`
	Price          float64   `json:"price"`
	DealTime       time.Time `json:"deal_time"`
	IsRollback     bool      `json:"is_rollback"`
	RollbackReason string    `json:"rollback_reason"`
	ArbitratorID   string    `json:"arbitrator_id"`
}

type TimerInfo struct {
	AuctionID  string `json:"auction_id"`
	Remaining  int64  `json:"remaining"`
	EndTime    int64  `json:"end_time"`
	IsExpired  bool   `json:"is_expired"`
	ServerTime int64  `json:"server_time"`
}

type Auctioneer struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Password string `json:"password"`
}

type HammerPriceRequest struct {
	AuctionID    string  `json:"auction_id"`
	AuctioneerID string  `json:"auctioneer_id"`
	BidID        string  `json:"bid_id"`
	Price        float64 `json:"price"`
	Remark       string  `json:"remark"`
}

type BidConflict struct {
	ID          string  `json:"id"`
	AuctionID   string  `json:"auction_id"`
	TimestampMs int64   `json:"timestamp_ms"`
	Bids        []*Bid  `json:"bids"`
	Resolved    bool    `json:"resolved"`
	ResolvedBy  string  `json:"resolved_by"`
	WinnerBidID string  `json:"winner_bid_id"`
	CreatedAt   time.Time `json:"created_at"`
}

type ArbitrationRequest struct {
	ConflictID   string `json:"conflict_id"`
	ArbitratorID string `json:"arbitrator_id"`
	WinnerBidID  string `json:"winner_bid_id"`
	Reason       string `json:"reason"`
}

type AuditLog struct {
	ID           string    `json:"id"`
	AuctionID    string    `json:"auction_id"`
	OperatorID   string    `json:"operator_id"`
	OperatorName string    `json:"operator_name"`
	Action       string    `json:"action"`
	BeforeData   string    `json:"before_data"`
	AfterData    string    `json:"after_data"`
	IP           string    `json:"ip"`
	Timestamp    time.Time `json:"timestamp"`
}

type PlaybackRequest struct {
	AuctionID string  `json:"auction_id"`
	Speed     float64 `json:"speed"`
	StartTime int64   `json:"start_time"`
	EndTime   int64   `json:"end_time"`
}

type ShardInfo struct {
	ShardID    int    `json:"shard_id"`
	ShardKey   string `json:"shard_key"`
	RedisAddr  string `json:"redis_addr"`
	LoadFactor int    `json:"load_factor"`
}

type ShardStats struct {
	ShardID       int   `json:"shard_id"`
	TotalAuctions int   `json:"total_auctions"`
	TotalBids     int   `json:"total_bids"`
	Connections   int   `json:"connections"`
}

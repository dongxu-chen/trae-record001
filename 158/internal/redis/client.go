package redis

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"math/big"
	"time"

	"auction-platform/internal/model"

	"github.com/redis/go-redis/v9"
)

var (
	MainClient *redis.Client
	ShardClients []*redis.Client
	ShardCount = 4
)

const (
	BidQueueLuaScript = `
local bid_queue_key = KEYS[1]
local bid_data = ARGV[1]
local request_id = ARGV[2]
local request_id_key = "bid_request:" .. request_id

local exists = redis.call("SETNX", request_id_key, 1)
if exists == 0 then
    return 0
end

redis.call("EXPIRE", request_id_key, 3600)
redis.call("LPUSH", bid_queue_key, bid_data)
return 1
`

	AuctionEndCheckLuaScript = `
local auction_id = KEYS[1]
local end_lock_key = "auction_end_lock:" .. auction_id
local current_time = tonumber(ARGV[1])
local end_time = tonumber(ARGV[2])

if current_time < end_time then
    return 0
end

local locked = redis.call("SETNX", end_lock_key, 1)
if locked == 0 then
    return 0
end

redis.call("EXPIRE", end_lock_key, 3600)
return 1
`

	UserBudgetLuaScript = `
local user_balance_key = "user_balance:" .. KEYS[1]
local auction_id = KEYS[2]
local bid_price = tonumber(ARGV[1])
local user_budget = tonumber(ARGV[2])
local request_id = ARGV[3]

local current_balance = redis.call("GET", user_balance_key)
if current_balance == false then
    current_balance = user_budget
else
    current_balance = tonumber(current_balance)
end

if current_balance < bid_price then
    return -1
end

local request_lock_key = "bid_request:" .. request_id
local exists = redis.call("SETNX", request_lock_key, 1)
if exists == 0 then
    return 0
end

redis.call("EXPIRE", request_lock_key, 3600)
redis.call("SET", user_balance_key, current_balance - bid_price, "EX", 86400)
return 1
`

	ConflictDetectLuaScript = `
local auction_id = KEYS[1]
local ms_timestamp = tonumber(ARGV[1])
local bid_id = ARGV[2]
local bid_data = ARGV[3]

local ms_key = "bid_ms:" .. auction_id .. ":" .. ms_timestamp
local count = redis.call("INCR", ms_key)
redis.call("EXPIRE", ms_key, 3600)

if count > 1 then
    local conflict_key = "conflict:" .. auction_id .. ":" .. ms_timestamp
    redis.call("RPUSH", conflict_key, bid_data)
    redis.call("EXPIRE", conflict_key, 86400)
    return 1
end

return 0
`
)

var (
	bidQueueScript      *redis.Script
	auctionEndCheckScript *redis.Script
	userBudgetScript    *redis.Script
	conflictDetectScript *redis.Script
)

func InitRedis(mainAddr string, shardAddrs []string, password string, db int) error {
	MainClient = redis.NewClient(&redis.Options{
		Addr:     mainAddr,
		Password: password,
		DB:       db,
		PoolSize: 100,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := MainClient.Ping(ctx).Err(); err != nil {
		return fmt.Errorf("main redis ping failed: %w", err)
	}

	for i, addr := range shardAddrs {
		client := redis.NewClient(&redis.Options{
			Addr:     addr,
			Password: password,
			DB:       db,
			PoolSize: 50,
		})
		if err := client.Ping(ctx).Err(); err != nil {
			return fmt.Errorf("shard %d redis ping failed: %w", i, err)
		}
		ShardClients = append(ShardClients, client)
	}

	bidQueueScript = redis.NewScript(BidQueueLuaScript)
	auctionEndCheckScript = redis.NewScript(AuctionEndCheckLuaScript)
	userBudgetScript = redis.NewScript(UserBudgetLuaScript)
	conflictDetectScript = redis.NewScript(ConflictDetectLuaScript)

	return nil
}

func GetShardByKey(key string) *redis.Client {
	h := sha256.New()
	h.Write([]byte(key))
	hash := h.Sum(nil)
	bigInt := new(big.Int).SetBytes(hash)
	shardID := bigInt.Mod(bigInt, big.NewInt(int64(len(ShardClients)))).Int64()
	return ShardClients[shardID]
}

func GetShardByAuctionID(auctionID string) *redis.Client {
	if len(ShardClients) == 0 {
		return MainClient
	}
	return GetShardByKey(auctionID)
}

func EnqueueBidAtomically(ctx context.Context, bidQueueKey string, bidData interface{}, requestID string) (bool, error) {
	data, err := json.Marshal(bidData)
	if err != nil {
		return false, err
	}

	result, err := bidQueueScript.Run(ctx, MainClient, []string{bidQueueKey}, string(data), requestID).Int()
	if err != nil {
		return false, err
	}
	return result == 1, nil
}

func CheckAndSetAuctionEndLock(ctx context.Context, auctionID string, currentTime int64, endTime int64) (bool, error) {
	result, err := auctionEndCheckScript.Run(ctx, MainClient, []string{auctionID}, currentTime, endTime).Int()
	if err != nil {
		return false, err
	}
	return result == 1, nil
}

func CheckUserBudgetAndReserve(ctx context.Context, userID string, auctionID string, bidPrice float64, userBudget float64, requestID string) (int, error) {
	result, err := userBudgetScript.Run(ctx, MainClient, []string{userID, auctionID}, bidPrice, userBudget, requestID).Int()
	if err != nil {
		return -2, err
	}
	return result, nil
}

func DetectBidConflict(ctx context.Context, auctionID string, msTimestamp int64, bid *model.Bid) (bool, error) {
	bidData, err := json.Marshal(bid)
	if err != nil {
		return false, err
	}

	result, err := conflictDetectScript.Run(ctx, MainClient, []string{auctionID}, msTimestamp, bid.ID, string(bidData)).Int()
	if err != nil {
		return false, err
	}
	return result == 1, nil
}

func GetConflicts(ctx context.Context, auctionID string) ([]*model.BidConflict, error) {
	keys, err := MainClient.Keys(ctx, fmt.Sprintf("conflict:%s:*", auctionID)).Result()
	if err != nil {
		return nil, err
	}

	conflicts := make([]*model.BidConflict, 0, len(keys))
	for _, key := range keys {
		bidDataList, err := MainClient.LRange(ctx, key, 0, -1).Result()
		if err != nil {
			continue
		}

		bids := make([]*model.Bid, 0, len(bidDataList))
		for _, bidData := range bidDataList {
			var bid model.Bid
			if err := json.Unmarshal([]byte(bidData), &bid); err == nil {
				bids = append(bids, &bid)
			}
		}

		if len(bids) > 0 {
			conflict := &model.BidConflict{
				ID:          key,
				AuctionID:   auctionID,
				Bids:        bids,
				Resolved:    false,
				CreatedAt:   time.Now(),
			}
			conflicts = append(conflicts, conflict)
		}
	}

	return conflicts, nil
}

func ResolveConflict(ctx context.Context, conflictID string, winnerBidID string, arbitratorID string, reason string) error {
	conflictKey := fmt.Sprintf("resolved_conflict:%s", conflictID)
	data := map[string]interface{}{
		"winner_bid_id": winnerBidID,
		"arbitrator_id": arbitratorID,
		"reason": reason,
		"resolved_at": time.Now().Unix(),
	}
	jsonData, _ := json.Marshal(data)
	return MainClient.Set(ctx, conflictKey, jsonData, 7*24*time.Hour).Err()
}

func SetUserBalance(ctx context.Context, userID string, balance float64) error {
	return MainClient.Set(ctx, fmt.Sprintf("user_balance:%s", userID), balance, 24*time.Hour).Err()
}

func GetUserBalance(ctx context.Context, userID string) (float64, error) {
	return MainClient.Get(ctx, fmt.Sprintf("user_balance:%s", userID)).Float64()
}

func RefundUserBalance(ctx context.Context, userID string, amount float64) error {
	key := fmt.Sprintf("user_balance:%s", userID)
	current, err := MainClient.Get(ctx, key).Float64()
	if err != nil && err != redis.Nil {
		return err
	}
	return MainClient.Set(ctx, key, current+amount, 24*time.Hour).Err()
}

func SaveAuditLog(ctx context.Context, log *model.AuditLog) error {
	logKey := fmt.Sprintf("audit_log:%s", log.ID)
	auctionLogKey := fmt.Sprintf("auction_audit:%s", log.AuctionID)
	
	data, err := json.Marshal(log)
	if err != nil {
		return err
	}

	pipe := MainClient.Pipeline()
	pipe.Set(ctx, logKey, data, 30*24*time.Hour)
	pipe.LPush(ctx, auctionLogKey, log.ID)
	pipe.Expire(ctx, auctionLogKey, 30*24*time.Hour)
	_, err = pipe.Exec(ctx)
	return err
}

func GetAuditLogs(ctx context.Context, auctionID string, limit int64) ([]*model.AuditLog, error) {
	auctionLogKey := fmt.Sprintf("auction_audit:%s", auctionID)
	logIDs, err := MainClient.LRange(ctx, auctionLogKey, 0, limit-1).Result()
	if err != nil {
		return nil, err
	}

	logs := make([]*model.AuditLog, 0, len(logIDs))
	for _, logID := range logIDs {
		logKey := fmt.Sprintf("audit_log:%s", logID)
		data, err := MainClient.Get(ctx, logKey).Result()
		if err != nil {
			continue
		}
		var log model.AuditLog
		if err := json.Unmarshal([]byte(data), &log); err == nil {
			logs = append(logs, &log)
		}
	}
	return logs, nil
}

func GetBidsSortedByTime(ctx context.Context, auctionID string) ([]*model.Bid, error) {
	historyKey := fmt.Sprintf("bid_history:%s", auctionID)
	results, err := MainClient.LRange(ctx, historyKey, 0, -1).Result()
	if err != nil {
		return nil, err
	}

	bids := make([]*model.Bid, 0, len(results))
	for _, result := range results {
		var bid model.Bid
		if err := json.Unmarshal([]byte(result), &bid); err == nil {
			bids = append(bids, &bid)
		}
	}
	
	for i, j := 0, len(bids)-1; i < j; i, j = i+1, j-1 {
		bids[i], bids[j] = bids[j], bids[i]
	}
	return bids, nil
}

func RecordHammerPrice(ctx context.Context, auctionID string, bidID string, auctioneerID string, price float64, remark string) error {
	key := fmt.Sprintf("hammer_price:%s", auctionID)
	data := map[string]interface{}{
		"auction_id": auctionID,
		"bid_id": bidID,
		"auctioneer_id": auctioneerID,
		"price": price,
		"remark": remark,
		"timestamp": time.Now().Unix(),
	}
	jsonData, _ := json.Marshal(data)
	return MainClient.Set(ctx, key, jsonData, 7*24*time.Hour).Err()
}

func RollbackDeal(ctx context.Context, dealRecordID string, reason string, arbitratorID string) error {
	dealKey := fmt.Sprintf("deal_record:%s", dealRecordID)
	data, err := MainClient.Get(ctx, dealKey).Result()
	if err != nil {
		return err
	}

	var deal model.DealRecord
	if err := json.Unmarshal([]byte(data), &deal); err != nil {
		return err
	}

	deal.IsRollback = true
	deal.RollbackReason = reason
	deal.ArbitratorID = arbitratorID

	newData, _ := json.Marshal(deal)
	if err := MainClient.Set(ctx, dealKey, newData, 7*24*time.Hour).Err(); err != nil {
		return err
	}

	if err := RefundUserBalance(ctx, deal.UserID, deal.Price); err != nil {
		return err
	}

	return nil
}

func GetShardStats(ctx context.Context) ([]*model.ShardStats, error) {
	stats := make([]*model.ShardStats, 0, len(ShardClients))
	for i, client := range ShardClients {
		auctionCount, _ := client.DBSize(ctx).Result()
		stats = append(stats, &model.ShardStats{
			ShardID:       i,
			TotalAuctions: int(auctionCount),
			TotalBids:     0,
			Connections:   client.PoolStats().TotalConns,
		})
	}
	return stats, nil
}

func Get(ctx context.Context, key string, dest interface{}) error {
	data, err := MainClient.Get(ctx, key).Result()
	if err != nil {
		return err
	}
	return json.Unmarshal([]byte(data), dest)
}

func Set(ctx context.Context, key string, value interface{}, expiration time.Duration) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return MainClient.Set(ctx, key, data, expiration).Err()
}

func Del(ctx context.Context, keys ...string) error {
	return MainClient.Del(ctx, keys...).Err()
}

func Exists(ctx context.Context, key string) (bool, error) {
	result, err := MainClient.Exists(ctx, key).Result()
	return result > 0, err
}

func SetNX(ctx context.Context, key string, value interface{}, expiration time.Duration) (bool, error) {
	data, err := json.Marshal(value)
	if err != nil {
		return false, err
	}
	return MainClient.SetNX(ctx, key, data, expiration).Result()
}

func HGet(ctx context.Context, key, field string, dest interface{}) error {
	data, err := MainClient.HGet(ctx, key, field).Result()
	if err != nil {
		return err
	}
	return json.Unmarshal([]byte(data), dest)
}

func HSet(ctx context.Context, key, field string, value interface{}) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return MainClient.HSet(ctx, key, field, data).Err()
}

func HGetAll(ctx context.Context, key string) (map[string]string, error) {
	return MainClient.HGetAll(ctx, key).Result()
}

func LPush(ctx context.Context, key string, value interface{}) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return MainClient.LPush(ctx, key, data).Err()
}

func RPop(ctx context.Context, key string, dest interface{}) error {
	data, err := MainClient.RPop(ctx, key).Result()
	if err != nil {
		return err
	}
	return json.Unmarshal([]byte(data), dest)
}

func LLen(ctx context.Context, key string) (int64, error) {
	return MainClient.LLen(ctx, key).Result()
}

func LRange(ctx context.Context, key string, start, stop int64) ([]string, error) {
	return MainClient.LRange(ctx, key, start, stop).Result()
}

func Publish(ctx context.Context, channel string, message interface{}) error {
	data, err := json.Marshal(message)
	if err != nil {
		return err
	}
	return MainClient.Publish(ctx, channel, data).Err()
}

func Subscribe(ctx context.Context, channel string) *redis.PubSub {
	return MainClient.Subscribe(ctx, channel)
}

func Incr(ctx context.Context, key string) (int64, error) {
	return MainClient.Incr(ctx, key).Result()
}

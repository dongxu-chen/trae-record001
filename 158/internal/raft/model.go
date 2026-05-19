package raft

import (
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"sync"
	"time"
)

type NodeState string

const (
	StateFollower  NodeState = "follower"
	StateCandidate NodeState = "candidate"
	StateLeader    NodeState = "leader"
)

const (
	DefaultHeartbeatInterval = 150 * time.Millisecond
	DefaultElectionTimeout   = 300 * time.Millisecond
	DefaultCommitTimeout     = 10 * time.Millisecond
	MaxLogEntriesPerAppend   = 100
)

type LogEntry struct {
	Index    uint64      `json:"index"`
	Term     uint64      `json:"term"`
	Command  interface{} `json:"command"`
	Checksum [32]byte    `json:"checksum"`
}

func (e *LogEntry) ComputeChecksum() [32]byte {
	h := sha256.New()
	binary.Write(h, binary.LittleEndian, e.Index)
	binary.Write(h, binary.LittleEndian, e.Term)
	if cmdBytes, ok := e.Command.([]byte); ok {
		h.Write(cmdBytes)
	} else {
		h.Write([]byte(fmt.Sprintf("%v", e.Command)))
	}
	copy(e.Checksum[:], h.Sum(nil))
	return e.Checksum
}

type BidCommand struct {
	Type        string  `json:"type"` 
	AuctionID   string  `json:"auction_id"`
	UserID      string  `json:"user_id"`
	Username    string  `json:"username"`
	Price       float64 `json:"price"`
	RequestID   string  `json:"request_id"`
	Timestamp   int64   `json:"timestamp"`
}

const (
	CommandTypeBid      = "bid"
	CommandTypeCreateAuction = "create_auction"
	CommandTypeConfirmDeal = "confirm_deal"
	CommandTypeRollback = "rollback"
)

type RaftState struct {
	mu            sync.RWMutex
	CurrentTerm   uint64
	VotedFor      string
	Log           []*LogEntry
	CommitIndex   uint64
	LastApplied   uint64
	NextIndex     map[string]uint64
	MatchIndex    map[string]uint64
}

type Server struct {
	ID          string
	Address     string
	Region      string
	IsLocal     bool
}

type VoteRequest struct {
	Term         uint64
	CandidateID  string
	LastLogIndex uint64
	LastLogTerm  uint64
}

type VoteResponse struct {
	Term        uint64
	VoteGranted bool
	From        string
}

type AppendEntriesRequest struct {
	Term         uint64
	LeaderID     string
	PrevLogIndex uint64
	PrevLogTerm  uint64
	Entries      []*LogEntry
	LeaderCommit uint64
}

type AppendEntriesResponse struct {
	Term          uint64
	Success       bool
	MatchIndex    uint64
	LastLogIndex  uint64
	ConflictIndex uint64
	ConflictTerm  uint64
	From          string
}

type InstallSnapshotRequest struct {
	Term              uint64
	LeaderID          string
	LastIncludedIndex uint64
	LastIncludedTerm  uint64
	Offset            uint64
	Data              []byte
	Done              bool
}

type InstallSnapshotResponse struct {
	Term    uint64
	Success bool
}

type ApplyResult struct {
	Index   uint64
	Error   error
	Result  interface{}
}

type RaftConfig struct {
	NodeID            string
	NodeAddr          string
	Region            string
	PeerAddrs         map[string]string
	HeartbeatInterval time.Duration
	ElectionTimeout   time.Duration
	DataDir           string
	MaxLogSize        int64
	SnapshotThreshold uint64
}

type ClusterState struct {
	LeaderID     string
	CurrentTerm  uint64
	NodeStates   map[string]NodeState
	LastUpdate   time.Time
}

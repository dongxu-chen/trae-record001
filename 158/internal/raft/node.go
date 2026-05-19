package raft

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"
)

type Node struct {
	config   *RaftConfig
	state    *RaftState
	nodeState NodeState
	leaderID  string

	transport Transport
	stateMachine StateMachine

	applyCh chan *ApplyResult

	heartbeatTimer *time.Timer
	electionTimer  *time.Timer

	shutdownCh chan struct{}
	running    int32

	mu sync.RWMutex
}

type Transport interface {
	RequestVote(ctx context.Context, target string, req *VoteRequest) (*VoteResponse, error)
	AppendEntries(ctx context.Context, target string, req *AppendEntriesRequest) (*AppendEntriesResponse, error)
	InstallSnapshot(ctx context.Context, target string, req *InstallSnapshotRequest) (*InstallSnapshotResponse, error)
	Listen(addr string, handler *Node) error
	Close() error
}

type StateMachine interface {
	Apply(entry *LogEntry) (interface{}, error)
	Snapshot() ([]byte, error)
	Restore(snapshot []byte) error
}

func NewNode(config *RaftConfig, stateMachine StateMachine, transport Transport) (*Node, error) {
	if config.HeartbeatInterval == 0 {
		config.HeartbeatInterval = DefaultHeartbeatInterval
	}
	if config.ElectionTimeout == 0 {
		config.ElectionTimeout = DefaultElectionTimeout
	}

	state := &RaftState{
		Log:        make([]*LogEntry, 1),
		NextIndex:  make(map[string]uint64),
		MatchIndex: make(map[string]uint64),
	}
	state.Log[0] = &LogEntry{Index: 0, Term: 0}

	if err := os.MkdirAll(config.DataDir, 0755); err != nil {
		return nil, err
	}

	if err := loadState(config.DataDir, state); err != nil {
		log.Printf("No existing state found, starting fresh: %v", err)
	}

	node := &Node{
		config:       config,
		state:        state,
		nodeState:    StateFollower,
		stateMachine: stateMachine,
		transport:    transport,
		applyCh:      make(chan *ApplyResult, 1024),
		shutdownCh:   make(chan struct{}),
	}

	for peerID := range config.PeerAddrs {
		node.state.NextIndex[peerID] = 1
		node.state.MatchIndex[peerID] = 0
	}

	return node, nil
}

func (n *Node) Start() error {
	if !atomic.CompareAndSwapInt32(&n.running, 0, 1) {
		return errors.New("node already running")
	}

	go n.runLoop()
	go n.applyLoop()

	if n.transport != nil {
		go n.transport.Listen(n.config.NodeAddr, n)
	}

	log.Printf("Raft node %s started in region %s", n.config.NodeID, n.config.Region)
	return nil
}

func (n *Node) Stop() error {
	if !atomic.CompareAndSwapInt32(&n.running, 1, 0) {
		return nil
	}

	close(n.shutdownCh)
	n.saveState()
	return n.transport.Close()
}

func (n *Node) runLoop() {
	n.resetElectionTimer()

	for {
		select {
		case <-n.shutdownCh:
			return
		case <-n.heartbeatTimer.C:
			n.mu.Lock()
			state := n.nodeState
			n.mu.Unlock()

			if state == StateLeader {
				n.sendHeartbeats()
				n.resetHeartbeatTimer()
			}
		case <-n.electionTimer.C:
			n.mu.Lock()
			state := n.nodeState
			n.mu.Unlock()

			if state != StateLeader {
				n.startElection()
			}
		}
	}
}

func (n *Node) startElection() {
	n.mu.Lock()
	defer n.mu.Unlock()

	n.state.CurrentTerm++
	n.nodeState = StateCandidate
	n.state.VotedFor = n.config.NodeID

	log.Printf("Node %s starting election for term %d", n.config.NodeID, n.state.CurrentTerm)

	lastLog := n.lastLog()
	req := &VoteRequest{
		Term:         n.state.CurrentTerm,
		CandidateID:  n.config.NodeID,
		LastLogIndex: lastLog.Index,
		LastLogTerm:  lastLog.Term,
	}

	voteCh := make(chan *VoteResponse, len(n.config.PeerAddrs))
	votesGranted := 1

	for peerID := range n.config.PeerAddrs {
		go func(peer string) {
			ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
			defer cancel()

			resp, err := n.transport.RequestVote(ctx, peer, req)
			if err != nil {
				log.Printf("RequestVote to %s failed: %v", peer, err)
				voteCh <- nil
				return
			}
			voteCh <- resp
		}(peerID)
	}

	for i := 0; i < len(n.config.PeerAddrs); i++ {
		select {
		case resp := <-voteCh:
			if resp == nil {
				continue
			}

			if resp.Term > n.state.CurrentTerm {
				n.becomeFollower(resp.Term)
				return
			}

			if resp.VoteGranted {
				votesGranted++
			}
		case <-time.After(500 * time.Millisecond):
		}
	}

	if votesGranted > n.quorumSize() {
		n.becomeLeader()
	} else {
		n.resetElectionTimer()
	}
}

func (n *Node) becomeLeader() {
	log.Printf("Node %s became leader for term %d", n.config.NodeID, n.state.CurrentTerm)
	n.nodeState = StateLeader
	n.leaderID = n.config.NodeID

	lastLog := n.lastLog()
	for peerID := range n.config.PeerAddrs {
		n.state.NextIndex[peerID] = lastLog.Index + 1
		n.state.MatchIndex[peerID] = 0
	}

	n.sendHeartbeats()
	n.resetHeartbeatTimer()
}

func (n *Node) becomeFollower(term uint64) {
	log.Printf("Node %s becoming follower for term %d", n.config.NodeID, term)
	n.state.CurrentTerm = term
	n.state.VotedFor = ""
	n.nodeState = StateFollower
	n.resetElectionTimer()
}

func (n *Node) sendHeartbeats() {
	for peerID := range n.config.PeerAddrs {
		go n.replicateTo(peerID)
	}
}

func (n *Node) replicateTo(peerID string) {
	n.mu.RLock()
	nextIdx := n.state.NextIndex[peerID]
	lastLog := n.lastLog()

	prevLogIndex := nextIdx - 1
	prevLogTerm := uint64(0)
	if prevLogIndex > 0 && int(prevLogIndex) < len(n.state.Log) {
		prevLogTerm = n.state.Log[prevLogIndex].Term
	}

	var entries []*LogEntry
	if nextIdx <= lastLog.Index {
		end := int(nextIdx) + MaxLogEntriesPerAppend
		if end > len(n.state.Log) {
			end = len(n.state.Log)
		}
		entries = n.state.Log[nextIdx:end]
	}

	req := &AppendEntriesRequest{
		Term:         n.state.CurrentTerm,
		LeaderID:     n.config.NodeID,
		PrevLogIndex: prevLogIndex,
		PrevLogTerm:  prevLogTerm,
		Entries:      entries,
		LeaderCommit: n.state.CommitIndex,
	}
	state := n.nodeState
	n.mu.RUnlock()

	if state != StateLeader {
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	resp, err := n.transport.AppendEntries(ctx, peerID, req)
	if err != nil {
		log.Printf("AppendEntries to %s failed: %v", peerID, err)
		return
	}

	n.mu.Lock()
	defer n.mu.Unlock()

	if resp.Term > n.state.CurrentTerm {
		n.becomeFollower(resp.Term)
		return
	}

	if n.nodeState != StateLeader {
		return
	}

	if resp.Success {
		if len(entries) > 0 {
			n.state.MatchIndex[peerID] = entries[len(entries)-1].Index
			n.state.NextIndex[peerID] = n.state.MatchIndex[peerID] + 1
		}
		n.advanceCommitIndex()
	} else {
		if resp.ConflictTerm > 0 {
			idx := n.findLastIndexOfTerm(resp.ConflictTerm)
			if idx > 0 {
				n.state.NextIndex[peerID] = idx + 1
			} else {
				n.state.NextIndex[peerID] = resp.ConflictIndex
			}
		} else {
			n.state.NextIndex[peerID] = resp.ConflictIndex
		}
		if n.state.NextIndex[peerID] < 1 {
			n.state.NextIndex[peerID] = 1
		}
	}
}

func (n *Node) advanceCommitIndex() {
	lastLog := n.lastLog()
	for newCommit := n.state.CommitIndex + 1; newCommit <= lastLog.Index; newCommit++ {
		matchCount := 1
		for peerID := range n.config.PeerAddrs {
			if n.state.MatchIndex[peerID] >= newCommit {
				matchCount++
			}
		}

		if matchCount > n.quorumSize() {
			if newCommit < uint64(len(n.state.Log)) && n.state.Log[newCommit].Term == n.state.CurrentTerm {
				n.state.CommitIndex = newCommit
			}
		} else {
			break
		}
	}
}

func (n *Node) applyLoop() {
	for {
		select {
		case <-n.shutdownCh:
			return
		default:
		}

		n.mu.RLock()
		commitIdx := n.state.CommitIndex
		lastApplied := n.state.LastApplied
		n.mu.RUnlock()

		if lastApplied >= commitIdx {
			time.Sleep(1 * time.Millisecond)
			continue
		}

		for i := lastApplied + 1; i <= commitIdx; i++ {
			select {
			case <-n.shutdownCh:
				return
			default:
			}

			n.mu.RLock()
			entry := n.state.Log[i]
			n.mu.RUnlock()

			result, err := n.stateMachine.Apply(entry)

			select {
			case n.applyCh <- &ApplyResult{
				Index:  i,
				Error:  err,
				Result: result,
			}:
			default:
			}

			n.mu.Lock()
			n.state.LastApplied = i
			n.mu.Unlock()
		}
	}
}

func (n *Node) HandleRequestVote(req *VoteRequest) (*VoteResponse, error) {
	n.mu.Lock()
	defer n.mu.Unlock()

	if req.Term < n.state.CurrentTerm {
		return &VoteResponse{
			Term:        n.state.CurrentTerm,
			VoteGranted: false,
			From:        n.config.NodeID,
		}, nil
	}

	if req.Term > n.state.CurrentTerm {
		n.becomeFollower(req.Term)
	}

	lastLog := n.lastLog()
	logOk := req.LastLogTerm > lastLog.Term || 
		(req.LastLogTerm == lastLog.Term && req.LastLogIndex >= lastLog.Index)

	canVote := (n.state.VotedFor == "" || n.state.VotedFor == req.CandidateID) && logOk

	if canVote {
		n.state.VotedFor = req.CandidateID
		n.resetElectionTimer()
	}

	return &VoteResponse{
		Term:        n.state.CurrentTerm,
		VoteGranted: canVote,
		From:        n.config.NodeID,
	}, nil
}

func (n *Node) HandleAppendEntries(req *AppendEntriesRequest) (*AppendEntriesResponse, error) {
	n.mu.Lock()
	defer n.mu.Unlock()

	if req.Term < n.state.CurrentTerm {
		return &AppendEntriesResponse{
			Term:          n.state.CurrentTerm,
			Success:       false,
			LastLogIndex:  n.lastLog().Index,
			From:          n.config.NodeID,
		}, nil
	}

	if req.Term > n.state.CurrentTerm || n.nodeState != StateFollower {
		n.becomeFollower(req.Term)
	}

	n.leaderID = req.LeaderID
	n.resetElectionTimer()

	if req.PrevLogIndex > 0 {
		if req.PrevLogIndex >= uint64(len(n.state.Log)) {
			return &AppendEntriesResponse{
				Term:          n.state.CurrentTerm,
				Success:       false,
				ConflictIndex: n.lastLog().Index + 1,
				LastLogIndex:  n.lastLog().Index,
				From:          n.config.NodeID,
			}, nil
		}

		if n.state.Log[req.PrevLogIndex].Term != req.PrevLogTerm {
			conflictTerm := n.state.Log[req.PrevLogIndex].Term
			conflictIdx := req.PrevLogIndex
			for conflictIdx > 0 && n.state.Log[conflictIdx].Term == conflictTerm {
				conflictIdx--
			}
			return &AppendEntriesResponse{
				Term:          n.state.CurrentTerm,
				Success:       false,
				ConflictIndex: conflictIdx + 1,
				ConflictTerm:  conflictTerm,
				LastLogIndex:  n.lastLog().Index,
				From:          n.config.NodeID,
			}, nil
		}
	}

	if len(req.Entries) > 0 {
		insertIdx := req.PrevLogIndex + 1
		for i, entry := range req.Entries {
			idx := insertIdx + uint64(i)
			if idx >= uint64(len(n.state.Log)) {
				n.state.Log = append(n.state.Log, entry)
			} else if n.state.Log[idx].Term != entry.Term {
				n.state.Log = n.state.Log[:idx]
				n.state.Log = append(n.state.Log, entry)
			}
		}
	}

	if req.LeaderCommit > n.state.CommitIndex {
		lastNewIndex := n.lastLog().Index
		if req.LeaderCommit < lastNewIndex {
			n.state.CommitIndex = req.LeaderCommit
		} else {
			n.state.CommitIndex = lastNewIndex
		}
	}

	return &AppendEntriesResponse{
		Term:         n.state.CurrentTerm,
		Success:      true,
		MatchIndex:   n.lastLog().Index,
		LastLogIndex: n.lastLog().Index,
		From:         n.config.NodeID,
	}, nil
}

func (n *Node) SubmitCommand(command interface{}) (uint64, error) {
	n.mu.RLock()
	state := n.nodeState
	n.mu.RUnlock()

	if state != StateLeader {
		return 0, errors.New("not leader")
	}

	entry := &LogEntry{
		Term:    n.state.CurrentTerm,
		Command: command,
	}
	entry.ComputeChecksum()

	n.mu.Lock()
	entry.Index = n.lastLog().Index + 1
	n.state.Log = append(n.state.Log, entry)
	n.mu.Unlock()

	go n.sendHeartbeats()

	return entry.Index, nil
}

func (n *Node) ApplyCh() <-chan *ApplyResult {
	return n.applyCh
}

func (n *Node) State() NodeState {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.nodeState
}

func (n *Node) LeaderID() string {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.leaderID
}

func (n *Node) CurrentTerm() uint64 {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.state.CurrentTerm
}

func (n *Node) CommitIndex() uint64 {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.state.CommitIndex
}

func (n *Node) GetClusterState() *ClusterState {
	n.mu.RLock()
	defer n.mu.RUnlock()

	nodeStates := make(map[string]NodeState)
	nodeStates[n.config.NodeID] = n.nodeState
	for id := range n.config.PeerAddrs {
		nodeStates[id] = StateFollower
	}
	nodeStates[n.leaderID] = StateLeader

	return &ClusterState{
		LeaderID:    n.leaderID,
		CurrentTerm: n.state.CurrentTerm,
		NodeStates:  nodeStates,
		LastUpdate:  time.Now(),
	}
}

func (n *Node) lastLog() *LogEntry {
	return n.state.Log[len(n.state.Log)-1]
}

func (n *Node) quorumSize() int {
	return len(n.config.PeerAddrs)/2 + 1
}

func (n *Node) findLastIndexOfTerm(term uint64) uint64 {
	for i := len(n.state.Log) - 1; i >= 0; i-- {
		if n.state.Log[i].Term == term {
			return uint64(i)
		}
	}
	return 0
}

func (n *Node) resetElectionTimer() {
	if n.electionTimer == nil {
		n.electionTimer = time.NewTimer(n.randomElectionTimeout())
	} else {
		n.electionTimer.Reset(n.randomElectionTimeout())
	}
}

func (n *Node) resetHeartbeatTimer() {
	if n.heartbeatTimer == nil {
		n.heartbeatTimer = time.NewTimer(n.config.HeartbeatInterval)
	} else {
		n.heartbeatTimer.Reset(n.config.HeartbeatInterval)
	}
}

func (n *Node) randomElectionTimeout() time.Duration {
	timeout := n.config.ElectionTimeout + time.Duration(rand.Int63n(int64(n.config.ElectionTimeout)))
	return timeout
}

func (n *Node) saveState() error {
	data, err := json.Marshal(n.state)
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(n.config.DataDir, "raft.state"), data, 0644)
}

func loadState(dataDir string, state *RaftState) error {
	data, err := os.ReadFile(filepath.Join(dataDir, "raft.state"))
	if err != nil {
		return err
	}
	return json.Unmarshal(data, state)
}

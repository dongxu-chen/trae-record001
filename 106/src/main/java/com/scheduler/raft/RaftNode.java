package com.scheduler.raft;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

@Slf4j
@Data
@Component
public class RaftNode {

    public enum NodeState {
        FOLLOWER, CANDIDATE, LEADER
    }

    @Value("${raft.node-id}")
    private String nodeId;

    @Value("${raft.election-timeout:5000")
    private long electionTimeout;

    @Value("${raft.heartbeat-interval:1000")
    private long heartbeatInterval;

    private volatile NodeState state = NodeState.FOLLOWER;
    private volatile String currentLeader;
    private volatile long currentTerm = 0;
    private volatile String votedFor;

    private final Map<String, String> peerAddresses = new ConcurrentHashMap<>();
    private final List<RaftLog> raftLog = new RaftLog();

    private final AtomicLong commitIndex = new AtomicLong(0);
    private final AtomicLong lastApplied = new AtomicLong(0);

    private final Map<String, Long> nextIndex = new ConcurrentHashMap<>();
    private final Map<String, Long> matchIndex = new ConcurrentHashMap<>();

    private ScheduledExecutorService scheduler;
    private ScheduledFuture<?> electionTimer;
    private ScheduledFuture<?> heartbeatTimer;

    private final AtomicBoolean running = new AtomicBoolean(false);
    private final List<Consumer<NodeState>> stateChangeListeners = new CopyOnWriteArrayList<>();

    private final Random random = new Random();

    @PostConstruct
    public void init() {
        scheduler = Executors.newScheduledThreadPool(2);
        running.set(true);
        resetElectionTimer();
        log.info("Raft节点 {} 初始化完成，初始状态: {}", nodeId, state);
    }

    @PreDestroy
    public void shutdown() {
        running.set(false);
        if (electionTimer != null) electionTimer.cancel(false);
        if (heartbeatTimer != null) heartbeatTimer.cancel(false);
        if (scheduler != null) scheduler.shutdown();
        log.info("Raft节点 {} 已关闭", nodeId);
    }

    private void resetElectionTimer() {
        if (electionTimer != null) {
            electionTimer.cancel(false);
        }
        long timeout = electionTimeout + random.nextInt(1000);
        electionTimer = scheduler.schedule(this::startElection, timeout, TimeUnit.MILLISECONDS);
    }

    private void resetHeartbeatTimer() {
        if (heartbeatTimer != null) {
            heartbeatTimer.cancel(false);
        }
        heartbeatTimer = scheduler.scheduleAtFixedRate(
                this::sendHeartbeats, 0, heartbeatInterval, TimeUnit.MILLISECONDS);
    }

    public synchronized void startElection() {
        if (!running.get()) return;

        state = NodeState.CANDIDATE;
        currentTerm++;
        votedFor = nodeId;
        log.info("节点 {} 开始选举，任期: {}", nodeId, currentTerm);

        int votesGranted = 1;
        int totalNodes = peerAddresses.size() + 1;

        for (Map.Entry<String, String> entry : peerAddresses.entrySet()) {
            String peerId = entry.getKey();
            if (requestVote(peerId)) {
                votesGranted++;
            }
        }

        if (votesGranted > totalNodes / 2) {
            becomeLeader();
        } else {
            becomeFollower();
        }
    }

    private boolean requestVote(String peerId) {
        log.info("向节点 {} 请求投票，任期: {}", peerId, currentTerm);
        try {
            RaftMessage.VoteRequest request = new RaftMessage.VoteRequest();
            request.setTerm(currentTerm);
            request.setCandidateId(nodeId);
            request.setLastLogIndex(raftLog.getLastIndex());
            request.setLastLogTerm(raftLog.getLastTerm());

            return true;
        } catch (Exception e) {
            log.error("请求投票失败: {}", e.getMessage());
            return false;
        }
    }

    public synchronized RaftMessage.VoteResponse handleVoteRequest(RaftMessage.VoteRequest request) {
        RaftMessage.VoteResponse response = new RaftMessage.VoteResponse();
        response.setTerm(currentTerm);
        response.setVoteGranted(false);

        if (request.getTerm() < currentTerm) {
            return response;
        }

        if (request.getTerm() > currentTerm) {
            currentTerm = request.getTerm();
            becomeFollower();
        }

        if ((votedFor == null || votedFor.equals(request.getCandidateId()))
                && isLogUpToDate(request.getLastLogIndex(), request.getLastLogTerm())) {
            votedFor = request.getCandidateId();
            response.setVoteGranted(true);
            resetElectionTimer();
            log.info("节点 {} 投票给 {}", nodeId, request.getCandidateId());
        }

        return response;
    }

    private boolean isLogUpToDate(long lastLogIndex, long lastLogTerm) {
        long localLastIndex = raftLog.getLastIndex();
        long localLastTerm = raftLog.getLastTerm();

        if (lastLogTerm != localLastTerm) {
            return lastLogTerm > localLastTerm;
        }
        return lastLogIndex >= localLastIndex;
    }

    private synchronized void becomeLeader() {
        state = NodeState.LEADER;
        currentLeader = nodeId;
        log.info("节点 {} 成为Leader，任期: {}", nodeId, currentTerm);

        for (String peerId : peerAddresses.keySet()) {
            nextIndex.put(peerId, raftLog.getLastIndex() + 1);
            matchIndex.put(peerId, 0L);
        }

        resetHeartbeatTimer();
        notifyStateChange();
    }

    private synchronized void becomeFollower() {
        state = NodeState.FOLLOWER;
        if (heartbeatTimer != null) {
            heartbeatTimer.cancel(false);
        }
        resetElectionTimer();
        notifyStateChange();
        log.info("节点 {} 转为Follower状态", nodeId);
    }

    private void sendHeartbeats() {
        if (state != NodeState.LEADER) return;

        for (Map.Entry<String, String> entry : peerAddresses.entrySet()) {
            String peerId = entry.getKey();
            sendAppendEntries(peerId);
        }
    }

    private void sendAppendEntries(String peerId) {
        try {
            long prevLogIndex = nextIndex.getOrDefault(peerId, 1L) - 1;
            long prevLogTerm = 0;
            if (prevLogIndex > 0) {
                RaftLogEntry entry = raftLog.getEntry(prevLogIndex);
                if (entry != null) {
                    prevLogTerm = entry.getTerm();
                }
            }

            List<RaftLogEntry> entries = raftLog.getEntriesFrom(nextIndex.get(peerId));

            RaftMessage.AppendEntriesRequest request = new RaftMessage.AppendEntriesRequest();
            request.setTerm(currentTerm);
            request.setLeaderId(nodeId);
            request.setPrevLogIndex(prevLogIndex);
            request.setPrevLogTerm(prevLogTerm);
            request.setEntries(entries);
            request.setLeaderCommit(commitIndex.get());

        } catch (Exception e) {
            log.error("发送AppendEntries失败: {}", e.getMessage());
        }
    }

    public synchronized RaftMessage.AppendEntriesResponse handleAppendEntries(RaftMessage.AppendEntriesRequest request) {
        RaftMessage.AppendEntriesResponse response = new RaftMessage.AppendEntriesResponse();
        response.setTerm(currentTerm);
        response.setSuccess(false);

        if (request.getTerm() < currentTerm) {
            return response;
        }

        if (request.getTerm() > currentTerm) {
            currentTerm = request.getTerm();
        }

        currentLeader = request.getLeaderId();
        resetElectionTimer();
        response.setSuccess(true);

        if (state != NodeState.FOLLOWER) {
            becomeFollower();
        }

        if (request.getLeaderCommit() > commitIndex.get()) {
            long newCommitIndex = Math.min(request.getLeaderCommit(), raftLog.getLastIndex());
            commitIndex.set(newCommitIndex);
            applyCommittedEntries();
        }

        return response;
    }

    private void applyCommittedEntries() {
        while (lastApplied.get() < commitIndex.get()) {
            long applyIndex = lastApplied.incrementAndGet();
            RaftLogEntry entry = raftLog.getEntry(applyIndex);
            if (entry != null) {
                applyLogEntry(entry);
            }
        }
    }

    private void applyLogEntry(RaftLogEntry entry) {
        log.info("应用日志条目: {}", entry);
    }

    public void addPeer(String peerId, String address) {
        peerAddresses.put(peerId, address);
        nextIndex.put(peerId, raftLog.getLastIndex() + 1);
        matchIndex.put(peerId, 0L);
        log.info("添加对等节点: {} -> {}", peerId, address);
    }

    public void removePeer(String peerId) {
        peerAddresses.remove(peerId);
        nextIndex.remove(peerId);
        matchIndex.remove(peerId);
        log.info("移除对等节点: {}", peerId);
    }

    public void addStateChangeListener(Consumer<NodeState> listener) {
        stateChangeListeners.add(listener);
    }

    private void notifyStateChange() {
        for (Consumer<NodeState> listener : stateChangeListeners) {
            try {
                listener.accept(state);
            } catch (Exception e) {
                log.error("状态变更监听器执行失败", e);
            }
        }
    }

    public boolean isLeader() {
        return state == NodeState.LEADER;
    }

    public String getLeaderAddress() {
        if (currentLeader == null) return null;
        return peerAddresses.get(currentLeader);
    }

    public List<String> getPeerIds() {
        return new ArrayList<>(peerAddresses.keySet());
    }

    public Map<String, String> getPeerAddresses() {
        return new HashMap<>(peerAddresses);
    }

    public Map<String, String> getClusterInfo() {
        Map<String, String> info = new HashMap<>();
        info.put("nodeId", nodeId);
        info.put("state", state.name());
        info.put("currentLeader", currentLeader);
        info.put("currentTerm", String.valueOf(currentTerm));
        info.put("peerCount", String.valueOf(peerAddresses.size()));
        info.put("commitIndex", String.valueOf(commitIndex.get()));
        return info;
    }
}

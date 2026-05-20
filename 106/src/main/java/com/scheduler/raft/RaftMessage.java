package com.scheduler.raft;

import lombok.Data;

import java.util.List;

public class RaftMessage {

    @Data
    public static class VoteRequest {
        private long term;
        private String candidateId;
        private long lastLogIndex;
        private long lastLogTerm;
    }

    @Data
    public static class VoteResponse {
        private long term;
        private boolean voteGranted;
    }

    @Data
    public static class AppendEntriesRequest {
        private long term;
        private String leaderId;
        private long prevLogIndex;
        private long prevLogTerm;
        private List<RaftLogEntry> entries;
        private long leaderCommit;
    }

    @Data
    public static class AppendEntriesResponse {
        private long term;
        private boolean success;
    }

    @Data
    public static class ClusterJoinRequest {
        private String nodeId;
        private String address;
    }

    @Data
    public static class ClusterJoinResponse {
        private boolean success;
        private String message;
        private String leaderId;
        private List<String> peers;
    }
}

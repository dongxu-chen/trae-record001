package com.scheduler.raft;

import lombok.Data;

@Data
public class RaftLogEntry {
    private long index;
    private long term;
    private String type;
    private String data;
    private long timestamp;

    public RaftLogEntry() {
        this.timestamp = System.currentTimeMillis();
    }

    public RaftLogEntry(long index, long term, String type, String data) {
        this.index = index;
        this.term = term;
        this.type = type;
        this.data = data;
        this.timestamp = System.currentTimeMillis();
    }
}

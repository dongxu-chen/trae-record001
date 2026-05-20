package com.scheduler.raft;

import java.util.ArrayList;
import java.util.List;

public class RaftLog {
    private final List<RaftLogEntry> entries = new ArrayList<>();

    public synchronized long getLastIndex() {
        return entries.size();
    }

    public synchronized long getLastTerm() {
        if (entries.isEmpty()) {
            return 0;
        }
        return entries.get(entries.size() - 1).getTerm();
    }

    public synchronized RaftLogEntry getEntry(long index) {
        if (index <= 0 || index > entries.size()) {
            return null;
        }
        return entries.get((int) (index - 1));
    }

    public synchronized List<RaftLogEntry> getEntriesFrom(long startIndex) {
        if (startIndex <= 0 || startIndex > entries.size()) {
            return new ArrayList<>();
        }
        return new ArrayList<>(entries.subList((int) (startIndex - 1), entries.size()));
    }

    public synchronized void append(RaftLogEntry entry) {
        entry.setIndex(entries.size() + 1L);
        entries.add(entry);
    }

    public synchronized boolean removeFrom(long index) {
        if (index <= 0 || index > entries.size()) {
            return false;
        }
        while (entries.size() >= index) {
            entries.remove(entries.size() - 1);
        }
        return true;
    }

    public synchronized int size() {
        return entries.size();
    }
}

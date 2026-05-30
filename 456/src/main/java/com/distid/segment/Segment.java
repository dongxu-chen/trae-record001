package com.distid.segment;

import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;

@Slf4j
public class Segment {
    private final String bizTag;
    private volatile long maxId;
    private volatile long step;
    private final AtomicLong currentId;
    private volatile boolean initialized = false;
    private final ReentrantLock lock = new ReentrantLock();

    public Segment(String bizTag, long maxId, long step) {
        this.bizTag = bizTag;
        this.maxId = maxId;
        this.step = step;
        this.currentId = new AtomicLong(maxId - step);
    }

    public long nextId() {
        long id = currentId.incrementAndGet();
        if (id > maxId) {
            return -1;
        }
        return id;
    }

    public boolean isExhausted() {
        return currentId.get() >= maxId;
    }

    public double usage() {
        long used = currentId.get() - (maxId - step);
        return (double) used / step;
    }

    public String getBizTag() {
        return bizTag;
    }

    public long getMaxId() {
        return maxId;
    }

    public long getStep() {
        return step;
    }

    public long getCurrentId() {
        return currentId.get();
    }

    public void update(long newMaxId, long newStep) {
        this.maxId = newMaxId;
        this.step = newStep;
        this.currentId.set(newMaxId - newStep);
        this.initialized = true;
    }

    public ReentrantLock getLock() {
        return lock;
    }

    public boolean isInitialized() {
        return initialized;
    }
}

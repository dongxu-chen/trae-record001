package com.distid.segment;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.List;

@Slf4j
public class SegmentBuffer {
    private final String bizTag;
    private final Segment[] segments;
    private volatile int currentPos;
    private volatile boolean nextSegmentReady;
    private volatile boolean initialized;
    private final Object lock = new Object();

    public SegmentBuffer(String bizTag) {
        this.bizTag = bizTag;
        this.currentPos = 0;
        this.nextSegmentReady = false;
        this.initialized = false;
        this.segments = new Segment[2];
        this.segments[0] = new Segment(bizTag, 0, 0);
        this.segments[1] = new Segment(bizTag, 0, 0);
    }

    public long nextId() {
        if (!initialized) {
            throw new SegmentBufferExhaustedException("Segment buffer not initialized for bizTag=" + bizTag);
        }

        Segment current = segments[currentPos];
        long id = current.nextId();
        if (id != -1) {
            if (!nextSegmentReady && current.usage() >= 0.75) {
                triggerLoadNextSegment();
            }
            return id;
        }

        synchronized (lock) {
            current = segments[currentPos];
            id = current.nextId();
            if (id != -1) {
                return id;
            }

            if (!nextSegmentReady) {
                log.warn("Next segment not ready for bizTag={}, waiting...", bizTag);
            }

            while (!nextSegmentReady) {
                try {
                    lock.wait(100);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new SegmentBufferExhaustedException("Interrupted while waiting for next segment");
                }
            }

            currentPos = nextPos();
            nextSegmentReady = false;
            current = segments[currentPos];
            id = current.nextId();
            return id;
        }
    }

    public List<Long> nextIds(int count) {
        List<Long> ids = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            ids.add(nextId());
        }
        return ids;
    }

    private void triggerLoadNextSegment() {
        Thread loader = new Thread(() -> {
            try {
                loadNextSegment();
            } catch (Exception e) {
                log.error("Failed to load next segment for bizTag={}", bizTag, e);
            }
        }, "segment-loader-" + bizTag);
        loader.setDaemon(true);
        loader.start();
    }

    private void loadNextSegment() {
        Segment next = segments[nextPos()];
        nextSegmentReady = false;

        long nextMaxId = fetchNextMaxIdFromStore(next.getBizTag(), next.getStep());
        next.update(nextMaxId, next.getStep() > 0 ? next.getStep() : 1000);

        synchronized (lock) {
            nextSegmentReady = true;
            lock.notifyAll();
        }
        log.info("Loaded next segment for bizTag={}, maxId={}, step={}", bizTag, nextMaxId, next.getStep());
    }

    protected long fetchNextMaxIdFromStore(String bizTag, long currentStep) {
        return 0;
    }

    private int nextPos() {
        return 1 - currentPos;
    }

    public String getBizTag() {
        return bizTag;
    }

    public Segment getCurrentSegment() {
        return segments[currentPos];
    }

    public boolean isInitialized() {
        return initialized;
    }

    public void setInitialized(boolean initialized) {
        this.initialized = initialized;
    }

    public boolean isNextSegmentReady() {
        return nextSegmentReady;
    }

    public Segment[] getSegments() {
        return segments;
    }

    public Object getLock() {
        return lock;
    }
}

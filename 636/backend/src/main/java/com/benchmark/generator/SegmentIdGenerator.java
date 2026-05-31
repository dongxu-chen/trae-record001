package com.benchmark.generator;

import java.util.concurrent.atomic.AtomicLong;

public class SegmentIdGenerator implements IdGenerator {

    private final AtomicLong currentId;
    private final long segmentSize;

    public SegmentIdGenerator(long segmentSize) {
        this.segmentSize = segmentSize;
        this.currentId = new AtomicLong(0);
    }

    @Override
    public String nextId() {
        return String.valueOf(currentId.incrementAndGet());
    }

    public long getSegmentSize() {
        return segmentSize;
    }
}

package com.distid.snowflake;

public class ClockBackwardException extends RuntimeException {
    private final long backwardMs;

    public ClockBackwardException(long backwardMs) {
        super("Clock moved backwards by " + backwardMs + "ms");
        this.backwardMs = backwardMs;
    }

    public long getBackwardMs() {
        return backwardMs;
    }
}

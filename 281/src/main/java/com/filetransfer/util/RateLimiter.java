package com.filetransfer.util;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class RateLimiter {
    private final long maxBytesPerSecond;
    private long bytesRead = 0;
    private long startTime = 0;
    private static final long WINDOW_SIZE = 1000;

    public RateLimiter(long maxBytesPerSecond) {
        this.maxBytesPerSecond = maxBytesPerSecond;
        this.startTime = System.currentTimeMillis();
    }

    public synchronized void acquire(int bytes) throws InterruptedException {
        if (maxBytesPerSecond <= 0) {
            return;
        }

        bytesRead += bytes;
        long currentTime = System.currentTimeMillis();
        long elapsedTime = currentTime - startTime;

        if (elapsedTime >= WINDOW_SIZE) {
            double expectedTime = (bytesRead * 1000.0) / maxBytesPerSecond;
            if (expectedTime > elapsedTime) {
                long sleepTime = (long) (expectedTime - elapsedTime);
                if (sleepTime > 0) {
                    Thread.sleep(sleepTime);
                }
            }
            bytesRead = 0;
            startTime = System.currentTimeMillis();
        }
    }

    public void reset() {
        bytesRead = 0;
        startTime = System.currentTimeMillis();
    }
}

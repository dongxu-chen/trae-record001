package com.quota.management.algorithm;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TokenBucket implements Serializable {

    private static final long serialVersionUID = 1L;

    private String key;

    private long capacity;

    private long tokens;

    private long refillRate;

    private long lastRefillTime;

    private String granularity;

    private long version;

    public synchronized TokenBucketSnapshot refillAndGetSnapshot() {
        long now = System.currentTimeMillis();
        long elapsed = now - lastRefillTime;
        long newTokens = (elapsed * refillRate) / 1000;
        if (newTokens > 0) {
            tokens = Math.min(capacity, tokens + newTokens);
            lastRefillTime = now;
        }
        return new TokenBucketSnapshot(tokens, version);
    }

    public synchronized boolean tryConsumeWithVersion(long tokensToConsume, long expectedVersion) {
        if (version != expectedVersion) {
            return false;
        }
        refillAndGetSnapshot();
        if (tokens >= tokensToConsume) {
            tokens -= tokensToConsume;
            version++;
            return true;
        }
        return false;
    }

    public synchronized boolean tryConsume(long tokensToConsume) {
        refillAndGetSnapshot();
        if (tokens >= tokensToConsume) {
            tokens -= tokensToConsume;
            version++;
            return true;
        }
        return false;
    }

    public synchronized void refill() {
        long now = System.currentTimeMillis();
        long elapsed = now - lastRefillTime;
        long newTokens = (elapsed * refillRate) / 1000;
        if (newTokens > 0) {
            tokens = Math.min(capacity, tokens + newTokens);
            lastRefillTime = now;
        }
    }

    public synchronized long getAvailableTokens() {
        refillAndGetSnapshot();
        return tokens;
    }

    public synchronized void addTokens(long amount) {
        tokens = Math.min(capacity, tokens + amount);
        version++;
    }

    public synchronized void deductTokens(long amount) {
        tokens = Math.max(0, tokens - amount);
        version++;
    }

    public synchronized void reset() {
        tokens = capacity;
        lastRefillTime = System.currentTimeMillis();
        version++;
    }

    @Data
    @AllArgsConstructor
    public static class TokenBucketSnapshot implements Serializable {
        private static final long serialVersionUID = 1L;
        private long tokens;
        private long version;
    }
}

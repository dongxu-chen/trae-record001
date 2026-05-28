package com.datasync.common.util;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import lombok.extern.slf4j.Slf4j;

import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
public class GlobalTransactionManager {
    private final String datacenterId;
    private final String nodeId;
    private final AtomicLong sequence = new AtomicLong(0);
    private final Cache<String, Boolean> processedTransactions;
    private final long maxCacheSize;

    public GlobalTransactionManager(String datacenterId, String nodeId, long maxCacheSize, long expireMinutes) {
        this.datacenterId = datacenterId;
        this.nodeId = nodeId;
        this.maxCacheSize = maxCacheSize > 0 ? maxCacheSize : 100000;

        CacheBuilder<Object, Object> builder = CacheBuilder.newBuilder();
        if (expireMinutes > 0) {
            builder.expireAfterWrite(expireMinutes, TimeUnit.MINUTES);
        }
        builder.maximumSize(this.maxCacheSize);
        this.processedTransactions = builder.build();
    }

    public String generateGlobalTransactionId() {
        long seq = sequence.incrementAndGet();
        if (seq > 999999L) {
            sequence.set(0);
            seq = sequence.incrementAndGet();
        }
        return String.format("GTX_%s_%s_%d_%06d",
                datacenterId,
                nodeId,
                System.currentTimeMillis(),
                seq);
    }

    public String generateGlobalTransactionId(String businessKey) {
        if (businessKey != null && !businessKey.isEmpty()) {
            return String.format("GTX_%s_%s_%s",
                    datacenterId,
                    nodeId,
                    UUID.nameUUIDFromBytes(businessKey.getBytes()).toString().replace("-", ""));
        }
        return generateGlobalTransactionId();
    }

    public boolean isProcessed(String globalTransactionId) {
        if (globalTransactionId == null) {
            return false;
        }
        return processedTransactions.getIfPresent(globalTransactionId) != null;
    }

    public boolean markProcessed(String globalTransactionId) {
        if (globalTransactionId == null) {
            return false;
        }
        Boolean existing = processedTransactions.getIfPresent(globalTransactionId);
        if (existing != null) {
            return false;
        }
        processedTransactions.put(globalTransactionId, Boolean.TRUE);
        return true;
    }

    public boolean checkAndMarkProcessed(String globalTransactionId) {
        if (globalTransactionId == null) {
            return true;
        }
        if (isProcessed(globalTransactionId)) {
            log.debug("Global transaction already processed: {}", globalTransactionId);
            return false;
        }
        return markProcessed(globalTransactionId);
    }

    public long getProcessedCount() {
        return processedTransactions.size();
    }

    public void cleanUp() {
        processedTransactions.cleanUp();
        log.info("Cleaned up transaction cache, current size: {}", processedTransactions.size());
    }

    public boolean isLoopback(String globalTransactionId, String currentDatacenterId) {
        if (globalTransactionId == null) {
            return false;
        }
        return globalTransactionId.startsWith("GTX_" + currentDatacenterId + "_");
    }

    public String getDatacenterIdFromTx(String globalTransactionId) {
        if (globalTransactionId == null || !globalTransactionId.startsWith("GTX_")) {
            return null;
        }
        String[] parts = globalTransactionId.split("_");
        if (parts.length >= 2) {
            return parts[1];
        }
        return null;
    }
}

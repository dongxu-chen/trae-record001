package com.pushplatform.service;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.concurrent.TimeUnit;

@Service
public class CallbackIdempotentService {

    private static final Logger logger = LoggerFactory.getLogger(CallbackIdempotentService.class);

    private Cache<String, Boolean> callbackCache;

    @PostConstruct
    public void init() {
        callbackCache = CacheBuilder.newBuilder()
                .maximumSize(100000)
                .expireAfterWrite(24, TimeUnit.HOURS)
                .build();
        logger.info("Callback idempotent service initialized");
    }

    public boolean isProcessed(String callbackId) {
        if (callbackId == null || callbackId.isEmpty()) {
            return false;
        }
        
        Boolean processed = callbackCache.getIfPresent(callbackId);
        if (processed != null && processed) {
            logger.debug("Callback already processed, id: {}", callbackId);
            return true;
        }
        return false;
    }

    public boolean markProcessed(String callbackId) {
        if (callbackId == null || callbackId.isEmpty()) {
            return false;
        }
        
        if (isProcessed(callbackId)) {
            return false;
        }
        
        callbackCache.put(callbackId, true);
        logger.debug("Callback marked as processed, id: {}", callbackId);
        return true;
    }

    public void removeProcessed(String callbackId) {
        if (callbackId != null) {
            callbackCache.invalidate(callbackId);
        }
    }

    public long getProcessedCount() {
        return callbackCache.size();
    }

    public void clearAll() {
        callbackCache.invalidateAll();
        logger.info("Callback cache cleared");
    }
}

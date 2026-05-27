package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.ReorderPointDTO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class RedisCacheService {

    private final RedisTemplate<String, Object> redisTemplate;

    private static final String STOCK_KEY_PREFIX = "stock:warehouse:";
    private static final String REORDER_POINT_KEY = "reorder:point:";
    private static final String WARNING_KEY = "warning:pending:";
    private static final String LOCK_KEY_PREFIX = "lock:";
    private static final long CACHE_TTL_MINUTES = 30;
    private static final long LOCK_TTL_SECONDS = 300;

    public void cacheStockInfo(Long warehouseId, Long medicineId, Integer quantity) {
        String key = STOCK_KEY_PREFIX + warehouseId + ":medicine:" + medicineId;
        redisTemplate.opsForValue().set(key, quantity, CACHE_TTL_MINUTES, TimeUnit.MINUTES);
        log.debug("Cached stock info for warehouse {}, medicine {}: {}", warehouseId, medicineId, quantity);
    }

    public Integer getCachedStock(Long warehouseId, Long medicineId) {
        String key = STOCK_KEY_PREFIX + warehouseId + ":medicine:" + medicineId;
        Object value = redisTemplate.opsForValue().get(key);
        return value != null ? (Integer) value : null;
    }

    public void evictStockCache(Long warehouseId, Long medicineId) {
        String key = STOCK_KEY_PREFIX + warehouseId + ":medicine:" + medicineId;
        redisTemplate.delete(key);
        log.debug("Evicted stock cache for warehouse {}, medicine {}", warehouseId, medicineId);
    }

    public void cacheReorderPoint(Long warehouseId, Long medicineId, ReorderPointDTO reorderPoint) {
        String key = REORDER_POINT_KEY + warehouseId + ":" + medicineId;
        redisTemplate.opsForValue().set(key, reorderPoint, CACHE_TTL_MINUTES, TimeUnit.MINUTES);
        log.debug("Cached reorder point for warehouse {}, medicine {}", warehouseId, medicineId);
    }

    public ReorderPointDTO getCachedReorderPoint(Long warehouseId, Long medicineId) {
        String key = REORDER_POINT_KEY + warehouseId + ":" + medicineId;
        Object value = redisTemplate.opsForValue().get(key);
        return value != null ? (ReorderPointDTO) value : null;
    }

    public void evictReorderPointCache(Long warehouseId, Long medicineId) {
        String key = REORDER_POINT_KEY + warehouseId + ":" + medicineId;
        redisTemplate.delete(key);
        log.debug("Evicted reorder point cache for warehouse {}, medicine {}", warehouseId, medicineId);
    }

    public void cachePendingWarnings(Long warehouseId, List<?> warnings) {
        String key = WARNING_KEY + warehouseId;
        redisTemplate.opsForValue().set(key, warnings, 5, TimeUnit.MINUTES);
    }

    public boolean acquireLock(String operation, String identifier) {
        String key = LOCK_KEY_PREFIX + operation + ":" + identifier;
        Boolean acquired = redisTemplate.opsForValue()
                .setIfAbsent(key, "1", LOCK_TTL_SECONDS, TimeUnit.SECONDS);
        return Boolean.TRUE.equals(acquired);
    }

    public void releaseLock(String operation, String identifier) {
        String key = LOCK_KEY_PREFIX + operation + ":" + identifier;
        redisTemplate.delete(key);
    }

    public void evictAllStockCache() {
        var keys = redisTemplate.keys(STOCK_KEY_PREFIX + "*");
        if (keys != null && !keys.isEmpty()) {
            redisTemplate.delete(keys);
            log.debug("Evicted all stock caches, count: {}", keys.size());
        }
    }

    public void evictAllReorderPointCache() {
        var keys = redisTemplate.keys(REORDER_POINT_KEY + "*");
        if (keys != null && !keys.isEmpty()) {
            redisTemplate.delete(keys);
            log.debug("Evicted all reorder point caches, count: {}", keys.size());
        }
    }
}

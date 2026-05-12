package com.ecommerce.productcenter.service;

import com.ecommerce.productcenter.entity.Sku;
import com.ecommerce.productcenter.entity.StockLog;
import com.ecommerce.productcenter.repository.SkuRepository;
import com.ecommerce.productcenter.repository.StockLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class StockService {

    private final SkuRepository skuRepository;
    private final StockLogRepository stockLogRepository;
    private final RedisTemplate<String, Object> redisTemplate;

    private static final String STOCK_LOCK_PREFIX = "stock:lock:";
    private static final String STOCK_KEY_PREFIX = "stock:sku:";
    private static final long LOCK_EXPIRE_SECONDS = 30;
    private static final long CACHE_EXPIRE_SECONDS = 300;

    public boolean deductStock(Long skuId, int quantity, String orderNo) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("扣减数量必须大于0");
        }

        String lockKey = STOCK_LOCK_PREFIX + skuId;
        String lockValue = Thread.currentThread().getName() + "-" + System.currentTimeMillis();

        try {
            Boolean locked = redisTemplate.opsForValue()
                    .setIfAbsent(lockKey, lockValue, LOCK_EXPIRE_SECONDS, TimeUnit.SECONDS);

            if (locked == null || !locked) {
                log.warn("获取库存锁失败，skuId={}, orderNo={}", skuId, orderNo);
                return false;
            }

            log.debug("成功获取库存锁，skuId={}, orderNo={}", skuId, orderNo);

            return doDeductStock(skuId, quantity, orderNo);

        } finally {
            releaseLock(lockKey, lockValue);
        }
    }

    private boolean doDeductStock(Long skuId, int quantity, String orderNo) {
        Optional<Sku> skuOpt = skuRepository.findByIdAndActiveTrue(skuId);
        if (skuOpt.isEmpty()) {
            log.error("SKU不存在或已禁用，skuId={}", skuId);
            return false;
        }

        Sku sku = skuOpt.get();
        int beforeStock = sku.getStock();

        if (beforeStock < quantity) {
            log.warn("库存不足，skuId={}, 现有库存={}, 需扣减={}", skuId, beforeStock, quantity);
            return false;
        }

        int updatedCount = skuRepository.deductStock(skuId, quantity);
        if (updatedCount <= 0) {
            log.error("扣减库存失败，skuId={}, quantity={}", skuId, quantity);
            return false;
        }

        int afterStock = beforeStock - quantity;

        StockLog stockLog = StockLog.builder()
                .skuId(skuId)
                .orderNo(orderNo)
                .type(StockLog.StockType.DEDUCT)
                .quantity(-quantity)
                .beforeStock(beforeStock)
                .afterStock(afterStock)
                .remark("订单扣减库存")
                .build();
        stockLogRepository.save(stockLog);

        updateStockCache(skuId, afterStock);

        log.info("库存扣减成功，skuId={}, orderNo={}, before={}, after={}", skuId, orderNo, beforeStock, afterStock);
        return true;
    }

    public boolean increaseStock(Long skuId, int quantity, String remark) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("增加数量必须大于0");
        }

        String lockKey = STOCK_LOCK_PREFIX + skuId;
        String lockValue = Thread.currentThread().getName() + "-" + System.currentTimeMillis();

        try {
            Boolean locked = redisTemplate.opsForValue()
                    .setIfAbsent(lockKey, lockValue, LOCK_EXPIRE_SECONDS, TimeUnit.SECONDS);

            if (locked == null || !locked) {
                log.warn("获取库存锁失败，skuId={}", skuId);
                return false;
            }

            return doIncreaseStock(skuId, quantity, remark);

        } finally {
            releaseLock(lockKey, lockValue);
        }
    }

    private boolean doIncreaseStock(Long skuId, int quantity, String remark) {
        Optional<Sku> skuOpt = skuRepository.findById(skuId);
        if (skuOpt.isEmpty()) {
            log.error("SKU不存在，skuId={}", skuId);
            return false;
        }

        Sku sku = skuOpt.get();
        int beforeStock = sku.getStock();

        int updatedCount = skuRepository.increaseStock(skuId, quantity);
        if (updatedCount <= 0) {
            log.error("增加库存失败，skuId={}, quantity={}", skuId, quantity);
            return false;
        }

        int afterStock = beforeStock + quantity;

        StockLog stockLog = StockLog.builder()
                .skuId(skuId)
                .type(StockLog.StockType.INCREASE)
                .quantity(quantity)
                .beforeStock(beforeStock)
                .afterStock(afterStock)
                .remark(remark != null ? remark : "库存增加")
                .build();
        stockLogRepository.save(stockLog);

        updateStockCache(skuId, afterStock);

        log.info("库存增加成功，skuId={}, before={}, after={}", skuId, beforeStock, afterStock);
        return true;
    }

    public boolean releaseStock(Long skuId, int quantity, String orderNo) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("释放数量必须大于0");
        }

        String lockKey = STOCK_LOCK_PREFIX + skuId;
        String lockValue = Thread.currentThread().getName() + "-" + System.currentTimeMillis();

        try {
            Boolean locked = redisTemplate.opsForValue()
                    .setIfAbsent(lockKey, lockValue, LOCK_EXPIRE_SECONDS, TimeUnit.SECONDS);

            if (locked == null || !locked) {
                log.warn("获取库存锁失败，skuId={}, orderNo={}", skuId, orderNo);
                return false;
            }

            return doReleaseStock(skuId, quantity, orderNo);

        } finally {
            releaseLock(lockKey, lockValue);
        }
    }

    private boolean doReleaseStock(Long skuId, int quantity, String orderNo) {
        Optional<Sku> skuOpt = skuRepository.findById(skuId);
        if (skuOpt.isEmpty()) {
            log.error("SKU不存在，skuId={}", skuId);
            return false;
        }

        Sku sku = skuOpt.get();
        int beforeStock = sku.getStock();

        int updatedCount = skuRepository.increaseStock(skuId, quantity);
        if (updatedCount <= 0) {
            log.error("释放库存失败，skuId={}, quantity={}", skuId, quantity);
            return false;
        }

        int afterStock = beforeStock + quantity;

        StockLog stockLog = StockLog.builder()
                .skuId(skuId)
                .orderNo(orderNo)
                .type(StockLog.StockType.RELEASE)
                .quantity(quantity)
                .beforeStock(beforeStock)
                .afterStock(afterStock)
                .remark("订单释放库存")
                .build();
        stockLogRepository.save(stockLog);

        updateStockCache(skuId, afterStock);

        log.info("库存释放成功，skuId={}, orderNo={}, before={}, after={}", skuId, orderNo, beforeStock, afterStock);
        return true;
    }

    @Transactional(readOnly = true)
    public Integer getStock(Long skuId) {
        String cacheKey = STOCK_KEY_PREFIX + skuId;
        Object cachedStock = redisTemplate.opsForValue().get(cacheKey);
        if (cachedStock != null) {
            return (Integer) cachedStock;
        }

        Integer stock = skuRepository.findStockBySkuId(skuId);
        if (stock != null) {
            updateStockCache(skuId, stock);
        }
        return stock;
    }

    @Transactional(readOnly = true)
    public List<StockLog> getStockLogs(Long skuId) {
        return stockLogRepository.findBySkuIdOrderByCreatedAtDesc(skuId);
    }

    public boolean batchDeductStock(Map<Long, Integer> skuQuantityMap, String orderNo) {
        List<Long> sortedSkuIds = skuQuantityMap.keySet().stream().sorted().toList();

        List<String> lockKeys = sortedSkuIds.stream()
                .map(skuId -> STOCK_LOCK_PREFIX + skuId)
                .toList();
        String lockValue = Thread.currentThread().getName() + "-" + System.currentTimeMillis();

        try {
            for (String lockKey : lockKeys) {
                Boolean locked = redisTemplate.opsForValue()
                        .setIfAbsent(lockKey, lockValue, LOCK_EXPIRE_SECONDS, TimeUnit.SECONDS);
                if (locked == null || !locked) {
                    log.warn("批量扣减获取锁失败，lockKey={}", lockKey);
                    return false;
                }
            }

            for (Map.Entry<Long, Integer> entry : skuQuantityMap.entrySet()) {
                boolean success = doDeductStock(entry.getKey(), entry.getValue(), orderNo);
                if (!success) {
                    log.error("批量扣减库存失败，skuId={}, orderNo={}", entry.getKey(), orderNo);
                    return false;
                }
            }

            log.info("批量库存扣减成功，orderNo={}, skuCount={}", orderNo, skuQuantityMap.size());
            return true;

        } finally {
            for (String lockKey : lockKeys) {
                releaseLock(lockKey, lockValue);
            }
        }
    }

    private void updateStockCache(Long skuId, int stock) {
        String cacheKey = STOCK_KEY_PREFIX + skuId;
        redisTemplate.opsForValue().set(cacheKey, stock, CACHE_EXPIRE_SECONDS, TimeUnit.SECONDS);
    }

    private void releaseLock(String lockKey, String lockValue) {
        try {
            Object currentValue = redisTemplate.opsForValue().get(lockKey);
            if (lockValue.equals(currentValue)) {
                redisTemplate.delete(lockKey);
                log.debug("释放库存锁，lockKey={}", lockKey);
            }
        } catch (Exception e) {
            log.error("释放锁异常，lockKey={}", lockKey, e);
        }
    }
}

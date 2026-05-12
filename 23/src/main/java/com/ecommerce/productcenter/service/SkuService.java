package com.ecommerce.productcenter.service;

import com.ecommerce.productcenter.config.BloomFilterConfig;
import com.ecommerce.productcenter.entity.Sku;
import com.ecommerce.productcenter.repository.SkuRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.CachePut;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class SkuService {

    private final SkuRepository skuRepository;
    private final BloomFilterConfig bloomFilterConfig;
    private final org.springframework.data.redis.core.RedisTemplate<String, Object> redisTemplate;

    private static final String SKU_LOCK_PREFIX = "sku:lock:";
    private static final long LOCK_EXPIRE_SECONDS = 30;

    @Cacheable(value = "skus", key = "#pageable.pageNumber + '-' + #pageable.pageSize", condition = "#pageable.pageNumber < 10")
    @Transactional(readOnly = true)
    public Page<Sku> getAllSkus(Pageable pageable) {
        return skuRepository.findByActiveTrue(pageable);
    }

    @Cacheable(value = "sku", key = "#id")
    @Transactional(readOnly = true)
    public Optional<Sku> getSkuById(Long id) {
        if (!bloomFilterConfig.getSkuBloomFilter().mightContain(String.valueOf(id))) {
            log.debug("布隆过滤器判定SKU不存在，id={}", id);
            return Optional.empty();
        }
        return skuRepository.findByIdAndActiveTrue(id);
    }

    @Cacheable(value = "skusByProduct", key = "#productId")
    @Transactional(readOnly = true)
    public List<Sku> getSkusByProductId(Long productId) {
        return skuRepository.findByProductIdAndActiveTrue(productId);
    }

    @Transactional(readOnly = true)
    public Optional<Sku> getSkuByCode(String skuCode) {
        return skuRepository.findBySkuCode(skuCode);
    }

    @CachePut(value = "sku", key = "#result.id")
    @CacheEvict(value = {"skus", "skusByProduct"}, allEntries = true)
    public Sku createSku(Sku sku) {
        Sku saved = skuRepository.save(sku);
        bloomFilterConfig.addSku(String.valueOf(saved.getId()));
        log.info("SKU创建成功，id={}，已添加到布隆过滤器", saved.getId());
        return saved;
    }

    @CachePut(value = "sku", key = "#id")
    @CacheEvict(value = {"skus", "skusByProduct"}, allEntries = true)
    public Optional<Sku> updateSku(Long id, Sku skuDetails) {
        String lockKey = SKU_LOCK_PREFIX + id;
        String lockValue = Thread.currentThread().getName() + "-" + System.currentTimeMillis();

        try {
            Boolean locked = redisTemplate.opsForValue()
                    .setIfAbsent(lockKey, lockValue, LOCK_EXPIRE_SECONDS, TimeUnit.SECONDS);

            if (locked == null || !locked) {
                log.warn("获取SKU更新锁失败，id={}", id);
                throw new RuntimeException("SKU正在被其他操作修改，请稍后重试");
            }

            return skuRepository.findById(id)
                    .map(sku -> {
                        if (skuDetails.getSkuCode() != null) {
                            sku.setSkuCode(skuDetails.getSkuCode());
                        }
                        if (skuDetails.getSpecs() != null) {
                            sku.setSpecs(skuDetails.getSpecs());
                        }
                        if (skuDetails.getPrice() != null) {
                            sku.setPrice(skuDetails.getPrice());
                        }
                        if (skuDetails.getStock() != null) {
                            sku.setStock(skuDetails.getStock());
                        }
                        if (skuDetails.getImageUrl() != null) {
                            sku.setImageUrl(skuDetails.getImageUrl());
                        }
                        if (skuDetails.getActive() != null) {
                            sku.setActive(skuDetails.getActive());
                        }
                        return skuRepository.save(sku);
                    });

        } finally {
            releaseLock(lockKey, lockValue);
        }
    }

    @CacheEvict(value = {"sku", "skus", "skusByProduct"}, allEntries = true, key = "#id")
    public boolean deleteSku(Long id) {
        return skuRepository.findById(id)
                .map(sku -> {
                    sku.setActive(false);
                    skuRepository.save(sku);
                    log.info("SKU软删除成功，id={}", id);
                    return true;
                })
                .orElse(false);
    }

    @CacheEvict(value = {"sku", "skus", "skusByProduct"}, allEntries = true)
    public boolean hardDeleteSku(Long id) {
        if (skuRepository.existsById(id)) {
            skuRepository.deleteById(id);
            log.info("SKU硬删除成功，id={}", id);
            return true;
        }
        return false;
    }

    public void initBloomFilter() {
        log.info("开始初始化SKU布隆过滤器...");
        skuRepository.findAll().forEach(sku -> {
            bloomFilterConfig.addSku(String.valueOf(sku.getId()));
        });
        log.info("SKU布隆过滤器初始化完成");
    }

    private void releaseLock(String lockKey, String lockValue) {
        try {
            Object currentValue = redisTemplate.opsForValue().get(lockKey);
            if (lockValue.equals(currentValue)) {
                redisTemplate.delete(lockKey);
                log.debug("释放SKU锁，lockKey={}", lockKey);
            }
        } catch (Exception e) {
            log.error("释放锁异常，lockKey={}", lockKey, e);
        }
    }
}

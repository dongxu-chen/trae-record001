package com.ecommerce.productcenter.service;

import com.ecommerce.productcenter.config.BloomFilterConfig;
import com.ecommerce.productcenter.entity.Product;
import com.ecommerce.productcenter.repository.ProductRepository;
import jakarta.persistence.OptimisticLockingFailureException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.CachePut;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.EnableRetry;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@EnableRetry
@RequiredArgsConstructor
@Transactional
public class ProductService {

    private final ProductRepository productRepository;
    private final org.springframework.data.redis.core.RedisTemplate<String, Object> redisTemplate;
    private final BloomFilterConfig bloomFilterConfig;

    private static final String PRODUCT_LOCK_PREFIX = "product:lock:";
    private static final long LOCK_EXPIRE_SECONDS = 30;

    @Cacheable(value = "products", key = "#pageable.pageNumber + '-' + #pageable.pageSize", condition = "#pageable.pageNumber < 10")
    public Page<Product> getAllProducts(Pageable pageable) {
        return productRepository.findByActiveTrue(pageable);
    }

    @Cacheable(value = "product", key = "#id")
    @Transactional(readOnly = true)
    public Optional<Product> getProductById(Long id) {
        if (!bloomFilterConfig.getProductBloomFilter().mightContain(String.valueOf(id))) {
            log.debug("布隆过滤器判定商品不存在，id={}", id);
            return Optional.empty();
        }

        log.debug("布隆过滤器判定商品可能存在，查询DB，id={}", id);
        Optional<Product> product = productRepository.findByIdAndActiveTrue(id);
        
        if (product.isEmpty()) {
            log.warn("商品实际不存在，但布隆过滤器误判，id={}", id);
        }
        
        return product;
    }

    @Cacheable(value = "productsByCategory", key = "#category + '-' + #pageable.pageNumber + '-' + #pageable.pageSize")
    @Transactional(readOnly = true)
    public Page<Product> getProductsByCategory(String category, Pageable pageable) {
        return productRepository.findByCategoryAndActiveTrue(category, pageable);
    }

    @Cacheable(value = "productsSearch", key = "#keyword + '-' + #pageable.pageNumber + '-' + #pageable.pageSize")
    @Transactional(readOnly = true)
    public Page<Product> searchProducts(String keyword, Pageable pageable) {
        return productRepository.searchByNameOrCategory(keyword, pageable);
    }

    @CachePut(value = "product", key = "#result.id")
    @CacheEvict(value = {"products", "productsByCategory", "productsSearch"}, allEntries = true)
    public Product createProduct(Product product) {
        Product saved = productRepository.save(product);
        bloomFilterConfig.getProductBloomFilter().put(String.valueOf(saved.getId()));
        log.info("商品创建成功，id={}，已添加到布隆过滤器", saved.getId());
        return saved;
    }

    @Retryable(
        retryFor = {OptimisticLockingFailureException.class, ObjectOptimisticLockingFailureException.class},
        maxAttempts = 3,
        backoff = @Backoff(delay = 100, multiplier = 2)
    )
    @CachePut(value = "product", key = "#id")
    @CacheEvict(value = {"products", "productsByCategory", "productsSearch"}, allEntries = true)
    public Optional<Product> updateProduct(Long id, Product productDetails) {
        String lockKey = PRODUCT_LOCK_PREFIX + id;
        String lockValue = Thread.currentThread().getName() + "-" + System.currentTimeMillis();

        try {
            Boolean locked = redisTemplate.opsForValue()
                    .setIfAbsent(lockKey, lockValue, LOCK_EXPIRE_SECONDS, TimeUnit.SECONDS);

            if (locked == null || !locked) {
                log.warn("获取商品更新锁失败，id={}", id);
                throw new RuntimeException("商品正在被其他操作修改，请稍后重试");
            }

            log.debug("成功获取商品更新锁，id={}", id);

            return productRepository.findById(id)
                    .map(product -> {
                        if (productDetails.getVersion() != null && !productDetails.getVersion().equals(product.getVersion())) {
                            log.warn("Version mismatch for product id: {}. Expected: {}, Received: {}", 
                                id, product.getVersion(), productDetails.getVersion());
                        }
                        if (productDetails.getName() != null) {
                            product.setName(productDetails.getName());
                        }
                        if (productDetails.getDescription() != null) {
                            product.setDescription(productDetails.getDescription());
                        }
                        if (productDetails.getPrice() != null) {
                            product.setPrice(productDetails.getPrice());
                        }
                        if (productDetails.getStock() != null) {
                            product.setStock(productDetails.getStock());
                        }
                        if (productDetails.getCategory() != null) {
                            product.setCategory(productDetails.getCategory());
                        }
                        if (productDetails.getImageUrl() != null) {
                            product.setImageUrl(productDetails.getImageUrl());
                        }
                        if (productDetails.getActive() != null) {
                            product.setActive(productDetails.getActive());
                        }
                        Product saved = productRepository.save(product);
                        log.debug("Successfully updated product id: {}, new version: {}", id, saved.getVersion());
                        return saved;
                    });

        } finally {
            releaseLock(lockKey, lockValue);
        }
    }

    @Retryable(
        retryFor = {OptimisticLockingFailureException.class, ObjectOptimisticLockingFailureException.class},
        maxAttempts = 3,
        backoff = @Backoff(delay = 100, multiplier = 2)
    )
    @CacheEvict(value = {"product", "products", "productsByCategory", "productsSearch"}, allEntries = true, key = "#id")
    public boolean deleteProduct(Long id) {
        String lockKey = PRODUCT_LOCK_PREFIX + id;
        String lockValue = Thread.currentThread().getName() + "-" + System.currentTimeMillis();

        try {
            Boolean locked = redisTemplate.opsForValue()
                    .setIfAbsent(lockKey, lockValue, LOCK_EXPIRE_SECONDS, TimeUnit.SECONDS);

            if (locked == null || !locked) {
                log.warn("获取商品删除锁失败，id={}", id);
                throw new RuntimeException("商品正在被其他操作修改，请稍后重试");
            }

            return productRepository.findById(id)
                    .map(product -> {
                        product.setActive(false);
                        productRepository.save(product);
                        log.info("商品软删除成功，id={}", id);
                        return true;
                    })
                    .orElse(false);

        } finally {
            releaseLock(lockKey, lockValue);
        }
    }

    @CacheEvict(value = {"product", "products", "productsByCategory", "productsSearch"}, allEntries = true)
    public boolean hardDeleteProduct(Long id) {
        if (productRepository.existsById(id)) {
            productRepository.deleteById(id);
            log.info("商品硬删除成功，id={}", id);
            return true;
        }
        return false;
    }

    public void initBloomFilter() {
        log.info("开始初始化商品布隆过滤器...");
        productRepository.findAll().forEach(product -> {
            bloomFilterConfig.getProductBloomFilter().put(String.valueOf(product.getId()));
        });
        log.info("商品布隆过滤器初始化完成");
    }

    private void releaseLock(String lockKey, String lockValue) {
        try {
            Object currentValue = redisTemplate.opsForValue().get(lockKey);
            if (lockValue.equals(currentValue)) {
                redisTemplate.delete(lockKey);
                log.debug("释放商品锁，lockKey={}", lockKey);
            }
        } catch (Exception e) {
            log.error("释放锁异常，lockKey={}", lockKey, e);
        }
    }
}

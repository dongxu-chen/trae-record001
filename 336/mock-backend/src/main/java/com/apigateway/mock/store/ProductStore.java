package com.apigateway.mock.store;

import com.apigateway.mock.entity.Product;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Collection;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Component
public class ProductStore {

    private final ConcurrentHashMap<Long, Product> productMap = new ConcurrentHashMap<>();
    private final AtomicLong idGenerator = new AtomicLong(1);

    public ProductStore() {
        initMockData();
    }

    private void initMockData() {
        LocalDateTime now = LocalDateTime.now();
        for (int i = 1; i <= 20; i++) {
            Product product = Product.builder()
                    .id(idGenerator.getAndIncrement())
                    .name("商品" + i)
                    .description("这是商品" + i + "的描述信息")
                    .price(10.0 + i * 5.5)
                    .stock(100 - i * 3)
                    .category(i % 3 == 0 ? "电子产品" : i % 3 == 1 ? "图书" : "服装")
                    .createdAt(now)
                    .updatedAt(now)
                    .build();
            productMap.put(product.getId(), product);
        }
        log.info("商品模拟数据初始化完成，共{}条", productMap.size());
    }

    public Product save(Product product) {
        if (product.getId() == null) {
            product.setId(idGenerator.getAndIncrement());
        }
        LocalDateTime now = LocalDateTime.now();
        if (product.getCreatedAt() == null) {
            product.setCreatedAt(now);
        }
        product.setUpdatedAt(now);
        productMap.put(product.getId(), product);
        return product;
    }

    public Product findById(Long id) {
        return productMap.get(id);
    }

    public Collection<Product> findAll() {
        return productMap.values();
    }

    public boolean deleteById(Long id) {
        return productMap.remove(id) != null;
    }

    public boolean existsById(Long id) {
        return productMap.containsKey(id);
    }

    public long count() {
        return productMap.size();
    }
}

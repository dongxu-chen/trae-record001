package com.ecommerce.productcenter.config;

import com.google.common.hash.BloomFilter;
import com.google.common.hash.Funnels;
import jakarta.annotation.PostConstruct;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Getter
@Component
public class BloomFilterConfig {

    private static final int EXPECTED_INSERTIONS = 100000;
    private static final double FPP = 0.01;

    private BloomFilter<String> productBloomFilter;
    private BloomFilter<String> skuBloomFilter;

    @PostConstruct
    public void init() {
        productBloomFilter = BloomFilter.create(
                Funnels.stringFunnel(java.nio.charset.StandardCharsets.UTF_8),
                EXPECTED_INSERTIONS,
                FPP
        );

        skuBloomFilter = BloomFilter.create(
                Funnels.stringFunnel(java.nio.charset.StandardCharsets.UTF_8),
                EXPECTED_INSERTIONS * 5,
                FPP
        );

        log.info("布隆过滤器初始化完成，product预期容量={}, sku预期容量={}, 误判率={}", 
            EXPECTED_INSERTIONS, EXPECTED_INSERTIONS * 5, FPP);
    }

    public boolean productMightExist(String id) {
        return productBloomFilter.mightContain(id);
    }

    public boolean skuMightExist(String id) {
        return skuBloomFilter.mightContain(id);
    }

    public void addProduct(String id) {
        productBloomFilter.put(id);
    }

    public void addSku(String id) {
        skuBloomFilter.put(id);
    }
}

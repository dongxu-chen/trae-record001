package com.example.deduplication.bloom;

import com.example.deduplication.config.DeduplicationProperties;
import com.google.common.hash.BloomFilter;
import com.google.common.hash.Funnels;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RBloomFilter;
import org.redisson.api.RedissonClient;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.Duration;

@Slf4j
@Service
@RequiredArgsConstructor
public class BloomFilterService {

    private static final String BLOOM_FILTER_KEY = "deduplication:bloom-filter";
    private static final String CONFIRMATION_PREFIX = "deduplication:bloom:confirm:";

    private final DeduplicationProperties properties;
    private final RedissonClient redissonClient;
    private final ReactiveStringRedisTemplate redisTemplate;

    private BloomFilter<String> localBloomFilter;
    private RBloomFilter<String> distributedBloomFilter;

    @PostConstruct
    public void init() {
        DeduplicationProperties.BloomFilterConfig config = properties.getBloomFilter();

        localBloomFilter = BloomFilter.create(
                Funnels.stringFunnel(StandardCharsets.UTF_8),
                config.getExpectedInsertions(),
                config.getFpp()
        );

        distributedBloomFilter = redissonClient.getBloomFilter(BLOOM_FILTER_KEY);
        distributedBloomFilter.tryInit(config.getExpectedInsertions(), config.getFpp());

        log.info("BloomFilter initialized - expectedInsertions: {}, fpp: {}, redisConfirmation: {}",
                config.getExpectedInsertions(), config.getFpp(), config.isRedisConfirmationEnabled());
    }

    public Mono<Boolean> mightContainWithConfirmation(String hash) {
        boolean localContains = localBloomFilter.mightContain(hash);
        boolean distributedContains = distributedBloomFilter.contains(hash);

        boolean bloomHit = localContains || distributedContains;

        if (!bloomHit) {
            return Mono.just(false);
        }

        if (!properties.getBloomFilter().isRedisConfirmationEnabled()) {
            return Mono.just(true);
        }

        String confirmationKey = CONFIRMATION_PREFIX + hash;
        return redisTemplate.hasKey(confirmationKey)
                .doOnNext(confirmed -> {
                    if (confirmed) {
                        log.debug("Bloom filter hit confirmed by Redis for hash: {}", hash);
                    } else {
                        log.debug("Bloom filter hit NOT confirmed by Redis (false positive) for hash: {}", hash);
                    }
                });
    }

    public Mono<Void> putWithConfirmation(String hash) {
        localBloomFilter.put(hash);
        distributedBloomFilter.add(hash);

        if (!properties.getBloomFilter().isRedisConfirmationEnabled()) {
            return Mono.empty();
        }

        String confirmationKey = CONFIRMATION_PREFIX + hash;
        return redisTemplate.opsForValue()
                .set(confirmationKey, "1", Duration.ofSeconds(properties.getBloomFilter().getConfirmationTtlSeconds()))
                .doOnNext(success -> {
                    if (success) {
                        log.debug("Bloom filter confirmation record set for hash: {}", hash);
                    }
                })
                .then();
    }

    @Deprecated
    public boolean mightContain(String hash) {
        boolean localContains = localBloomFilter.mightContain(hash);
        boolean distributedContains = distributedBloomFilter.contains(hash);

        if (localContains && !distributedContains) {
            distributedBloomFilter.add(hash);
        }

        return localContains || distributedContains;
    }

    @Deprecated
    public void put(String hash) {
        localBloomFilter.put(hash);
        distributedBloomFilter.add(hash);
    }
}

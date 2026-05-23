package com.gateway.service;

import com.gateway.config.GatewayProperties;
import com.gateway.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.util.Date;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class JwtBlacklistService {

    private final ReactiveRedisTemplate<String, Object> reactiveRedisTemplate;
    private final JwtUtil jwtUtil;
    private final GatewayProperties gatewayProperties;

    private static final String BLACKLIST_KEY_PREFIX = "jwt:blacklist:";

    public Mono<Boolean> blacklistToken(String token) {
        try {
            Date expiration = jwtUtil.extractExpiration(token);
            long ttl = expiration.getTime() - System.currentTimeMillis();

            if (ttl <= 0) {
                log.warn("Token already expired, no need to blacklist");
                return Mono.just(false);
            }

            String key = BLACKLIST_KEY_PREFIX + getTokenHash(token);

            return reactiveRedisTemplate.opsForValue()
                    .set(key, System.currentTimeMillis(), ttl, TimeUnit.MILLISECONDS)
                    .doOnSuccess(success -> {
                        if (success) {
                            log.info("Token added to blacklist, TTL: {}ms", ttl);
                        }
                    })
                    .onErrorResume(e -> {
                        log.error("Failed to blacklist token", e);
                        return Mono.just(false);
                    });
        } catch (Exception e) {
            log.error("Invalid token, cannot blacklist", e);
            return Mono.just(false);
        }
    }

    public Mono<Boolean> isBlacklisted(String token) {
        String key = BLACKLIST_KEY_PREFIX + getTokenHash(token);
        return reactiveRedisTemplate.hasKey(key)
                .doOnNext(isBlacklisted -> {
                    if (isBlacklisted) {
                        log.debug("Token is blacklisted");
                    }
                })
                .onErrorReturn(false);
    }

    public Mono<Boolean> blacklistToken(String token, long ttlMillis) {
        String key = BLACKLIST_KEY_PREFIX + getTokenHash(token);

        return reactiveRedisTemplate.opsForValue()
                .set(key, System.currentTimeMillis(), ttlMillis, TimeUnit.MILLISECONDS)
                .doOnSuccess(success -> {
                    if (success) {
                        log.info("Token added to blacklist with custom TTL: {}ms", ttlMillis);
                    }
                })
                .onErrorReturn(false);
    }

    public Mono<Long> getRemainingTtl(String token) {
        String key = BLACKLIST_KEY_PREFIX + getTokenHash(token);
        return reactiveRedisTemplate.getExpire(key, TimeUnit.MILLISECONDS)
                .onErrorReturn(-1L);
    }

    private String getTokenHash(String token) {
        try {
            int hash = token.hashCode();
            return Integer.toHexString(hash);
        } catch (Exception e) {
            return String.valueOf(token.hashCode());
        }
    }
}

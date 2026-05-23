package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.DomainRateLimit;
import com.emailmarketing.mapper.DomainRateLimitMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Service
public class DomainRateLimitService extends ServiceImpl<DomainRateLimitMapper, DomainRateLimit> {

    @Autowired
    private RedisTemplate<String, String> redisTemplate;

    @Value("${email.rate-limit.default-per-minute:10}")
    private int defaultLimitPerMinute;

    @Value("${email.rate-limit.redis-key-prefix:email:rate:}")
    private String redisKeyPrefix;

    private final Map<String, Integer> domainLimitCache = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        refreshDomainLimitCache();
    }

    public void refreshDomainLimitCache() {
        LambdaQueryWrapper<DomainRateLimit> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(DomainRateLimit::getStatus, 1);
        List<DomainRateLimit> limits = list(wrapper);
        domainLimitCache.clear();
        for (DomainRateLimit limit : limits) {
            domainLimitCache.put(limit.getDomain().toLowerCase(), limit.getLimitPerMinute());
        }
    }

    public boolean tryAcquire(String email) {
        String domain = extractDomain(email);
        int limit = getLimitForDomain(domain);
        String key = redisKeyPrefix + domain + ":" + System.currentTimeMillis() / 60000;
        
        Long count = redisTemplate.opsForValue().increment(key, 1);
        if (count == 1) {
            redisTemplate.expire(key, 61, TimeUnit.SECONDS);
        }
        
        return count <= limit;
    }

    public int getLimitForDomain(String domain) {
        return domainLimitCache.getOrDefault(domain.toLowerCase(), defaultLimitPerMinute);
    }

    public DomainRateLimit getOrCreateDomainLimit(String domain) {
        LambdaQueryWrapper<DomainRateLimit> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(DomainRateLimit::getDomain, domain.toLowerCase());
        DomainRateLimit rateLimit = getOne(wrapper);
        
        if (rateLimit == null) {
            rateLimit = new DomainRateLimit();
            rateLimit.setDomain(domain.toLowerCase());
            rateLimit.setLimitPerMinute(defaultLimitPerMinute);
            rateLimit.setStatus(1);
            save(rateLimit);
            refreshDomainLimitCache();
        }
        return rateLimit;
    }

    public boolean updateDomainLimit(String domain, int limitPerMinute) {
        DomainRateLimit rateLimit = getOrCreateDomainLimit(domain);
        rateLimit.setLimitPerMinute(limitPerMinute);
        boolean success = updateById(rateLimit);
        if (success) {
            refreshDomainLimitCache();
        }
        return success;
    }

    public List<DomainRateLimit> getAllDomainLimits() {
        LambdaQueryWrapper<DomainRateLimit> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByDesc(DomainRateLimit::getUpdatedAt);
        return list(wrapper);
    }

    private String extractDomain(String email) {
        int atIndex = email.indexOf('@');
        if (atIndex > 0 && atIndex < email.length() - 1) {
            return email.substring(atIndex + 1).toLowerCase();
        }
        return "default";
    }
}

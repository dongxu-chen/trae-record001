package com.shortlink.task;

import com.shortlink.service.ShortLinkService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.Set;

@Slf4j
@Component
@RequiredArgsConstructor
public class ShortLinkCleanupTask {

    private final ShortLinkService shortLinkService;
    private final RedisTemplate<String, Object> redisTemplate;

    private static final String REDIS_SHORT_LINK_PREFIX = "shortlink:code:";
    private static final String REDIS_UV_PREFIX = "shortlink:uv:";

    @Scheduled(cron = "${shortlink.cleanup.cron:0 0 2 * * ?}")
    public void cleanupExpiredShortLinks() {
        log.info("开始清理过期短链接...");

        try {
            int deletedCount = shortLinkService.deleteExpiredLinks();
            log.info("清理过期短链接完成，删除数量: {}", deletedCount);

            if (deletedCount > 0) {
                cleanupRedisCache();
            }
        } catch (Exception e) {
            log.error("清理过期短链接失败", e);
        }
    }

    private void cleanupRedisCache() {
        try {
            Set<String> keys = redisTemplate.keys(REDIS_SHORT_LINK_PREFIX + "*");
            if (keys != null && !keys.isEmpty()) {
                redisTemplate.delete(keys);
                log.info("清理Redis短链接缓存，数量: {}", keys.size());
            }
        } catch (Exception e) {
            log.warn("清理Redis短链接缓存失败", e);
        }
    }

    @Scheduled(cron = "0 0 3 * * ?")
    public void cleanupUvCache() {
        log.info("开始清理UV统计缓存...");

        try {
            Set<String> keys = redisTemplate.keys(REDIS_UV_PREFIX + "*");
            if (keys != null && !keys.isEmpty()) {
                redisTemplate.delete(keys);
                log.info("清理UV统计缓存完成，数量: {}", keys.size());
            }
        } catch (Exception e) {
            log.error("清理UV统计缓存失败", e);
        }
    }
}

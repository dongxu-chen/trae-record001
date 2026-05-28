package com.ratelimit.center.service;

import com.alibaba.fastjson.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.RateLimitConstants;
import com.ratelimit.center.entity.RateLimitLogEntity;
import com.ratelimit.center.mapper.RateLimitLogMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import javax.annotation.PostConstruct;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class RateLimitLogService {

    @Autowired
    private RateLimitLogMapper rateLimitLogMapper;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Value("${rate-limit.log.enabled:true}")
    private boolean logEnabled;

    @Value("${rate-limit.log.retain-days:30}")
    private int retainDays;

    @Value("${rate-limit.log.batch-size:100}")
    private int batchSize;

    private final BlockingQueue<RateLimitLogEntity> logQueue = new LinkedBlockingQueue<>(10000);

    @PostConstruct
    public void init() {
        if (logEnabled) {
            startLogConsumer();
            log.info("Rate limit log service initialized, retain days: {}, batch size: {}", retainDays, batchSize);
        }
    }

    private void startLogConsumer() {
        Thread consumerThread = new Thread(() -> {
            while (true) {
                try {
                    List<RateLimitLogEntity> batch = new ArrayList<>();
                    RateLimitLogEntity firstLog = logQueue.poll(5, TimeUnit.SECONDS);
                    if (firstLog != null) {
                        batch.add(firstLog);
                        logQueue.drainTo(batch, batchSize - 1);
                        saveBatch(batch);
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.error("Failed to consume rate limit log queue", e);
                }
            }
        }, "rate-limit-log-consumer");
        consumerThread.setDaemon(true);
        consumerThread.start();
    }

    public void log(RateLimitLogEntity logEntity) {
        if (!logEnabled) {
            return;
        }
        if (logEntity.getOccurTime() == null) {
            logEntity.setOccurTime(LocalDateTime.now());
        }
        try {
            if (!logQueue.offer(logEntity, 100, TimeUnit.MILLISECONDS)) {
                log.warn("Rate limit log queue is full, dropping log: {}", logEntity.getResource());
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    public void logAsync(String serviceName, String resource, String origin, String ruleType,
                         int passCount, int blockCount, long rt, String exception,
                         String clientIp, String requestPath, String requestMethod, String requestParams) {
        RateLimitLogEntity entity = new RateLimitLogEntity();
        entity.setServiceName(serviceName);
        entity.setResource(resource);
        entity.setOrigin(origin);
        entity.setRuleType(ruleType);
        entity.setPassCount(passCount);
        entity.setBlockCount(blockCount);
        entity.setRt(rt);
        entity.setException(exception);
        entity.setClientIp(clientIp);
        entity.setRequestPath(requestPath);
        entity.setRequestMethod(requestMethod);
        entity.setRequestParams(requestParams);
        entity.setOccurTime(LocalDateTime.now());
        log(entity);
    }

    private void saveBatch(List<RateLimitLogEntity> logs) {
        if (CollectionUtils.isEmpty(logs)) {
            return;
        }
        try {
            for (RateLimitLogEntity logEntity : logs) {
                rateLimitLogMapper.insert(logEntity);
            }
            log.debug("Saved {} rate limit logs", logs.size());
        } catch (Exception e) {
            log.error("Failed to save rate limit logs batch", e);
        }
    }

    public PageResult<RateLimitLogEntity> queryLogs(String serviceName, String resource, String ruleType,
                                                    LocalDateTime startTime, LocalDateTime endTime,
                                                    Integer page, Integer size) {
        LambdaQueryWrapper<RateLimitLogEntity> wrapper = new LambdaQueryWrapper<>();
        if (serviceName != null && !serviceName.isEmpty()) {
            wrapper.eq(RateLimitLogEntity::getServiceName, serviceName);
        }
        if (resource != null && !resource.isEmpty()) {
            wrapper.like(RateLimitLogEntity::getResource, resource);
        }
        if (ruleType != null && !ruleType.isEmpty()) {
            wrapper.eq(RateLimitLogEntity::getRuleType, ruleType);
        }
        if (startTime != null) {
            wrapper.ge(RateLimitLogEntity::getOccurTime, startTime);
        }
        if (endTime != null) {
            wrapper.le(RateLimitLogEntity::getOccurTime, endTime);
        }
        wrapper.orderByDesc(RateLimitLogEntity::getOccurTime);

        Page<RateLimitLogEntity> pageResult = rateLimitLogMapper.selectPage(new Page<>(page, size), wrapper);
        return PageResult.of(pageResult.getRecords(), pageResult.getTotal(), pageResult.getSize(), pageResult.getCurrent());
    }

    public Map<String, Object> getLogStats(String serviceName, LocalDateTime startTime, LocalDateTime endTime) {
        LambdaQueryWrapper<RateLimitLogEntity> wrapper = new LambdaQueryWrapper<>();
        if (serviceName != null && !serviceName.isEmpty()) {
            wrapper.eq(RateLimitLogEntity::getServiceName, serviceName);
        }
        if (startTime != null) {
            wrapper.ge(RateLimitLogEntity::getOccurTime, startTime);
        }
        if (endTime != null) {
            wrapper.le(RateLimitLogEntity::getOccurTime, endTime);
        }

        List<RateLimitLogEntity> logs = rateLimitLogMapper.selectList(wrapper);

        long totalPass = logs.stream().mapToLong(log -> log.getPassCount() != null ? log.getPassCount() : 0).sum();
        long totalBlock = logs.stream().mapToLong(log -> log.getBlockCount() != null ? log.getBlockCount() : 0).sum();
        double avgRt = logs.stream().mapToLong(log -> log.getRt() != null ? log.getRt() : 0).average().orElse(0);

        Map<String, Long> blockByRuleType = logs.stream()
                .filter(log -> log.getBlockCount() != null && log.getBlockCount() > 0)
                .collect(Collectors.groupingBy(
                        log -> log.getRuleType() != null ? log.getRuleType() : "unknown",
                        Collectors.summingLong(log -> log.getBlockCount() != null ? log.getBlockCount() : 0)
                ));

        Map<String, Long> blockByResource = logs.stream()
                .filter(log -> log.getBlockCount() != null && log.getBlockCount() > 0)
                .collect(Collectors.groupingBy(
                        RateLimitLogEntity::getResource,
                        Collectors.summingLong(log -> log.getBlockCount() != null ? log.getBlockCount() : 0)
                ));

        Map<String, Object> stats = new HashMap<>();
        stats.put("totalCount", logs.size());
        stats.put("totalPass", totalPass);
        stats.put("totalBlock", totalBlock);
        stats.put("avgRt", avgRt);
        stats.put("blockRate", totalPass + totalBlock > 0 ? (double) totalBlock / (totalPass + totalBlock) : 0);
        stats.put("blockByRuleType", blockByRuleType);
        stats.put("blockByResource", blockByResource);

        return stats;
    }

    @Scheduled(cron = "0 0 3 * * ?")
    public void cleanOldLogs() {
        if (!logEnabled) {
            return;
        }
        try {
            LocalDateTime expireTime = LocalDate.now().atStartOfDay().minusDays(retainDays);
            LambdaQueryWrapper<RateLimitLogEntity> wrapper = new LambdaQueryWrapper<>();
            wrapper.lt(RateLimitLogEntity::getOccurTime, expireTime);
            int deleted = rateLimitLogMapper.delete(wrapper);
            log.info("Cleaned {} old rate limit logs (older than {} days)", deleted, retainDays);
        } catch (Exception e) {
            log.error("Failed to clean old rate limit logs", e);
        }
    }
}

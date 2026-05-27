package com.datasecurity.masking.audit;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Component
public class InMemoryAuditLogStore implements AuditLogStore {

    private final List<AuditLog> auditLogs = new CopyOnWriteArrayList<>();

    private final Map<String, List<AuditLog>> userIndex = new ConcurrentHashMap<>();

    private final Map<String, List<AuditLog>> databaseIndex = new ConcurrentHashMap<>();

    private final Map<String, List<AuditLog>> tableIndex = new ConcurrentHashMap<>();

    @Autowired(required = false)
    private RedisTemplate<String, Object> redisTemplate;

    private static final String AUDIT_LOG_KEY = "data_masking:audit_logs";

    private static final int MAX_LOG_SIZE = 100000;

    @PostConstruct
    public void init() {
        log.info("In-memory audit log store initialized");
    }

    @Override
    public void save(AuditLog auditLog) {
        auditLog.setId(UUID.randomUUID().toString());
        auditLog.setTimestamp(System.currentTimeMillis());

        auditLogs.add(auditLog);

        addToIndex(userIndex, auditLog.getUserId(), auditLog);
        addToIndex(databaseIndex, auditLog.getDatabaseId(), auditLog);
        addToIndex(tableIndex, auditLog.getTableName(), auditLog);

        if (auditLogs.size() > MAX_LOG_SIZE) {
            auditLogs.remove(0);
        }

        if (redisTemplate != null) {
            try {
                redisTemplate.opsForList().rightPush(AUDIT_LOG_KEY, auditLog);
                redisTemplate.expire(AUDIT_LOG_KEY, 30, TimeUnit.DAYS);
            } catch (Exception e) {
                log.warn("Failed to save audit log to Redis", e);
            }
        }

        log.debug("Saved audit log: user={}, operation={}, table={}",
                auditLog.getUserId(), auditLog.getOperation(), auditLog.getTableName());
    }

    private void addToIndex(Map<String, List<AuditLog>> index, String key, AuditLog log) {
        if (key == null) return;
        index.computeIfAbsent(key, k -> new CopyOnWriteArrayList<>()).add(log);
    }

    @Override
    public List<AuditLog> findByUserId(String userId, long startTime, long endTime) {
        List<AuditLog> logs = userIndex.getOrDefault(userId, Collections.emptyList());
        return filterByTime(logs, startTime, endTime);
    }

    @Override
    public List<AuditLog> findByDatabaseId(String databaseId, long startTime, long endTime) {
        List<AuditLog> logs = databaseIndex.getOrDefault(databaseId, Collections.emptyList());
        return filterByTime(logs, startTime, endTime);
    }

    @Override
    public List<AuditLog> findByTableName(String tableName, long startTime, long endTime) {
        List<AuditLog> logs = tableIndex.getOrDefault(tableName, Collections.emptyList());
        return filterByTime(logs, startTime, endTime);
    }

    @Override
    public List<AuditLog> findBySensitiveType(String sensitiveType, long startTime, long endTime) {
        return auditLogs.stream()
                .filter(log -> log.getSensitiveTypes() != null && log.getSensitiveTypes().contains(sensitiveType))
                .filter(log -> isInTimeRange(log, startTime, endTime))
                .collect(Collectors.toList());
    }

    @Override
    public List<AuditLog> findByOperation(String operation, long startTime, long endTime) {
        return auditLogs.stream()
                .filter(log -> operation.equals(log.getOperation()))
                .filter(log -> isInTimeRange(log, startTime, endTime))
                .collect(Collectors.toList());
    }

    @Override
    public List<AuditLog> findAll(long startTime, long endTime, int page, int size) {
        List<AuditLog> filtered = filterByTime(auditLogs, startTime, endTime);

        int fromIndex = page * size;
        int toIndex = Math.min(fromIndex + size, filtered.size());

        if (fromIndex >= filtered.size()) {
            return Collections.emptyList();
        }

        return new ArrayList<>(filtered.subList(fromIndex, toIndex));
    }

    @Override
    public long count(long startTime, long endTime) {
        return filterByTime(auditLogs, startTime, endTime).size();
    }

    private List<AuditLog> filterByTime(List<AuditLog> logs, long startTime, long endTime) {
        return logs.stream()
                .filter(log -> isInTimeRange(log, startTime, endTime))
                .collect(Collectors.toList());
    }

    private boolean isInTimeRange(AuditLog log, long startTime, long endTime) {
        long ts = log.getTimestamp() != null ? log.getTimestamp() : 0;
        return ts >= startTime && ts <= endTime;
    }

    public void clearAll() {
        auditLogs.clear();
        userIndex.clear();
        databaseIndex.clear();
        tableIndex.clear();
        log.info("Cleared all audit logs");
    }
}

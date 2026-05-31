package com.datacheck.datasource;

import com.alibaba.fastjson2.JSON;
import com.datacheck.model.CheckTask;
import com.datacheck.model.DataRecord;
import com.datacheck.model.enums.DataSourceType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.*;

@Slf4j
@Component
public class RedisDataSourceAdapter implements DataSourceAdapter {

    private final RedisTemplate<String, Object> sourceRedisTemplate;
    private final RedisTemplate<String, Object> targetRedisTemplate;
    private final StringRedisTemplate sourceStringRedisTemplate;
    private final StringRedisTemplate targetStringRedisTemplate;

    @Autowired
    public RedisDataSourceAdapter(
            @Qualifier("sourceRedisTemplate") RedisTemplate<String, Object> sourceRedisTemplate,
            @Qualifier("targetRedisTemplate") RedisTemplate<String, Object> targetRedisTemplate,
            @Qualifier("sourceStringRedisTemplate") StringRedisTemplate sourceStringRedisTemplate,
            @Qualifier("targetStringRedisTemplate") StringRedisTemplate targetStringRedisTemplate) {
        this.sourceRedisTemplate = sourceRedisTemplate;
        this.targetRedisTemplate = targetRedisTemplate;
        this.sourceStringRedisTemplate = sourceStringRedisTemplate;
        this.targetStringRedisTemplate = targetStringRedisTemplate;
    }

    @Override
    public DataSourceType getType() {
        return DataSourceType.REDIS;
    }

    @Override
    public Iterator<DataRecord> iterateSource(CheckTask task) {
        return new RedisRecordIterator(sourceStringRedisTemplate, sourceRedisTemplate, task);
    }

    @Override
    public Iterator<DataRecord> iterateTarget(CheckTask task) {
        return new RedisRecordIterator(targetStringRedisTemplate, targetRedisTemplate, task);
    }

    @Override
    public DataRecord getSourceRecord(String key, CheckTask task) {
        return getRecord(sourceRedisTemplate, key, task);
    }

    @Override
    public DataRecord getTargetRecord(String key, CheckTask task) {
        return getRecord(targetRedisTemplate, key, task);
    }

    @Override
    public long getSourceCount(CheckTask task) {
        return getCount(sourceStringRedisTemplate, task);
    }

    @Override
    public long getTargetCount(CheckTask task) {
        return getCount(targetStringRedisTemplate, task);
    }

    @Override
    public boolean insertTarget(DataRecord record, CheckTask task) {
        return writeRecord(targetRedisTemplate, record, task);
    }

    @Override
    public boolean updateTarget(DataRecord record, CheckTask task) {
        return writeRecord(targetRedisTemplate, record, task);
    }

    @Override
    public boolean deleteTarget(String key, CheckTask task) {
        try {
            targetRedisTemplate.delete(key);
            log.info("Successfully deleted redis key: {}", key);
            return true;
        } catch (Exception e) {
            log.error("Failed to delete redis key: {}", key, e);
            return false;
        }
    }

    @Override
    public List<String> getPrimaryKeys(String tableName) {
        return Collections.singletonList("key");
    }

    @Override
    public List<String> getColumns(String tableName) {
        return Arrays.asList("key", "value");
    }

    @SuppressWarnings("unchecked")
    private DataRecord getRecord(RedisTemplate<String, Object> redisTemplate, String key, CheckTask task) {
        try {
            Object value = redisTemplate.opsForValue().get(key);
            if (value == null) {
                return null;
            }
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("key", key);
            if (value instanceof Map) {
                data.putAll((Map<String, Object>) value);
            } else {
                data.put("value", value);
            }
            return DataRecord.builder()
                    .key(key)
                    .data(data)
                    .sourceType(DataSourceType.REDIS)
                    .timestamp(System.currentTimeMillis())
                    .tableName(task.getTableName())
                    .build();
        } catch (Exception e) {
            log.error("Failed to get redis record, key: {}", key, e);
            return null;
        }
    }

    private long getCount(StringRedisTemplate stringRedisTemplate, CheckTask task) {
        try {
            String pattern = task.getTableName() + "*";
            ScanOptions options = ScanOptions.scanOptions().match(pattern).count(1000).build();
            long count = 0;
            try (Cursor<String> cursor = stringRedisTemplate.scan(options)) {
                while (cursor.hasNext()) {
                    cursor.next();
                    count++;
                }
            }
            return count;
        } catch (Exception e) {
            log.error("Failed to get redis count for pattern: {}", task.getTableName(), e);
            return 0;
        }
    }

    private boolean writeRecord(RedisTemplate<String, Object> redisTemplate, DataRecord record, CheckTask task) {
        try {
            Map<String, Object> data = new LinkedHashMap<>(record.getData());
            data.remove("key");
            Object value = data.size() == 1 && data.containsKey("value") ? data.get("value") : data;
            redisTemplate.opsForValue().set(record.getKey(), value);
            log.info("Successfully wrote redis key: {}", record.getKey());
            return true;
        } catch (Exception e) {
            log.error("Failed to write redis key: {}", record.getKey(), e);
            return false;
        }
    }

    private class RedisRecordIterator implements Iterator<DataRecord> {
        private final StringRedisTemplate stringRedisTemplate;
        private final RedisTemplate<String, Object> redisTemplate;
        private final CheckTask task;
        private final int batchSize;
        private Cursor<String> keyCursor;
        private List<String> currentBatch;
        private int currentIndex = 0;
        private boolean hasMore = true;

        public RedisRecordIterator(StringRedisTemplate stringRedisTemplate,
                                   RedisTemplate<String, Object> redisTemplate,
                                   CheckTask task) {
            this.stringRedisTemplate = stringRedisTemplate;
            this.redisTemplate = redisTemplate;
            this.task = task;
            this.batchSize = task.getBatchSize() != null ? task.getBatchSize() : 1000;
            initCursor();
        }

        private void initCursor() {
            try {
                String pattern = task.getTableName() + "*";
                ScanOptions options = ScanOptions.scanOptions()
                        .match(pattern)
                        .count(batchSize)
                        .build();
                keyCursor = stringRedisTemplate.scan(options);
                fetchNextBatch();
            } catch (Exception e) {
                log.error("Failed to initialize redis cursor for pattern: {}", task.getTableName(), e);
                hasMore = false;
                currentBatch = Collections.emptyList();
            }
        }

        private void fetchNextBatch() {
            try {
                currentBatch = new ArrayList<>();
                while (currentBatch.size() < batchSize && keyCursor.hasNext()) {
                    currentBatch.add(keyCursor.next());
                }
                if (currentBatch.isEmpty()) {
                    hasMore = false;
                    keyCursor.close();
                }
                currentIndex = 0;
            } catch (Exception e) {
                log.error("Failed to fetch redis batch", e);
                hasMore = false;
                currentBatch = Collections.emptyList();
            }
        }

        @Override
        public boolean hasNext() {
            if (currentIndex < currentBatch.size()) {
                return true;
            }
            if (hasMore) {
                fetchNextBatch();
                return currentIndex < currentBatch.size();
            }
            return false;
        }

        @SuppressWarnings("unchecked")
        @Override
        public DataRecord next() {
            if (!hasNext()) {
                throw new NoSuchElementException();
            }
            String key = currentBatch.get(currentIndex++);
            Object value = redisTemplate.opsForValue().get(key);
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("key", key);
            if (value instanceof Map) {
                data.putAll((Map<String, Object>) value);
            } else {
                data.put("value", value);
            }
            return DataRecord.builder()
                    .key(key)
                    .data(data)
                    .sourceType(DataSourceType.REDIS)
                    .timestamp(System.currentTimeMillis())
                    .tableName(task.getTableName())
                    .build();
        }
    }
}

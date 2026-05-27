package com.datasecurity.masking.service;

import com.datasecurity.masking.model.DatabaseConfig;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.scanner.MetadataScanner;
import com.datasecurity.masking.scanner.MetadataScannerFactory;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class MetadataService {

    private static final String METADATA_CACHE_PREFIX = "data_masking:metadata:";

    @Autowired
    private MetadataScannerFactory scannerFactory;

    @Autowired(required = false)
    private RedisTemplate<String, Object> redisTemplate;

    private final Map<String, List<SensitiveField>> localCache = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        log.info("MetadataService initialized");
    }

    public List<SensitiveField> scanDatabase(DatabaseConfig config) {
        log.info("Starting metadata scan for database: {}", config.getName());
        MetadataScanner scanner = scannerFactory.getScanner(config);
        List<SensitiveField> fields = scanner.scan(config);

        localCache.put(config.getId(), fields);

        if (redisTemplate != null) {
            String cacheKey = METADATA_CACHE_PREFIX + config.getId();
            redisTemplate.opsForValue().set(cacheKey, fields, 24, TimeUnit.HOURS);
        }

        log.info("Metadata scan completed for database: {}, found {} sensitive fields",
                config.getName(), fields.size());
        return fields;
    }

    public List<SensitiveField> getSensitiveFields(String databaseId) {
        List<SensitiveField> fields = localCache.get(databaseId);
        if (fields != null) {
            return fields;
        }

        if (redisTemplate != null) {
            String cacheKey = METADATA_CACHE_PREFIX + databaseId;
            @SuppressWarnings("unchecked")
            List<SensitiveField> cachedFields = (List<SensitiveField>) redisTemplate.opsForValue().get(cacheKey);
            if (cachedFields != null) {
                localCache.put(databaseId, cachedFields);
                return cachedFields;
            }
        }

        return null;
    }

    public void refreshMetadata(DatabaseConfig config) {
        log.info("Refreshing metadata for database: {}", config.getName());
        scanDatabase(config);
    }
}

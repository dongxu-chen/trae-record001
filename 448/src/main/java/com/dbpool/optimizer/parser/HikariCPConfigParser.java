package com.dbpool.optimizer.parser;

import com.dbpool.optimizer.model.PoolConfig;
import com.dbpool.optimizer.model.PoolType;
import org.springframework.stereotype.Component;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Properties;

@Component
public class HikariCPConfigParser implements PoolConfigParser {

    @Override
    public PoolConfig parse(Map<String, String> configMap) {
        return PoolConfig.builder()
                .poolType(PoolType.HIKARICP)
                .maxPoolSize(getInt(configMap, "maximumPoolSize", 10))
                .minIdle(getInt(configMap, "minimumIdle", 10))
                .connectionTimeoutMs(getLong(configMap, "connectionTimeout", 30000))
                .idleTimeoutMs(getLong(configMap, "idleTimeout", 600000))
                .maxLifetimeMs(getLong(configMap, "maxLifetime", 1800000))
                .leakDetectionThresholdMs(getLong(configMap, "leakDetectionThreshold", 0))
                .validationQuery(configMap.getOrDefault("connectionTestQuery", "SELECT 1"))
                .testOnBorrow(false)
                .testOnReturn(false)
                .testWhileIdle(false)
                .timeBetweenEvictionRunsMs(0)
                .numTestsPerEvictionRun(0)
                .build();
    }

    @Override
    public PoolConfig parseProperties(Properties properties) {
        Map<String, String> configMap = new LinkedHashMap<>();
        for (String name : properties.stringPropertyNames()) {
            String key = name.startsWith("spring.datasource.hikari.")
                    ? name.substring("spring.datasource.hikari.".length())
                    : name.startsWith("hikari.") ? name.substring("hikari.".length()) : name;
            configMap.put(key, properties.getProperty(name));
        }
        return parse(configMap);
    }

    @Override
    public Map<String, String> exportConfig(PoolConfig config) {
        Map<String, String> configMap = new LinkedHashMap<>();
        configMap.put("spring.datasource.hikari.maximumPoolSize", String.valueOf(config.getMaxPoolSize()));
        configMap.put("spring.datasource.hikari.minimumIdle", String.valueOf(config.getMinIdle()));
        configMap.put("spring.datasource.hikari.connectionTimeout", String.valueOf(config.getConnectionTimeoutMs()));
        configMap.put("spring.datasource.hikari.idleTimeout", String.valueOf(config.getIdleTimeoutMs()));
        configMap.put("spring.datasource.hikari.maxLifetime", String.valueOf(config.getMaxLifetimeMs()));
        configMap.put("spring.datasource.hikari.leakDetectionThreshold", String.valueOf(config.getLeakDetectionThresholdMs()));
        configMap.put("spring.datasource.hikari.connectionTestQuery", config.getValidationQuery());
        return configMap;
    }

    @Override
    public Properties exportProperties(PoolConfig config) {
        Properties properties = new Properties();
        exportConfig(config).forEach(properties::setProperty);
        return properties;
    }

    @Override
    public String getPoolTypeName() {
        return "HikariCP";
    }

    private int getInt(Map<String, String> configMap, String key, int defaultValue) {
        try {
            String value = configMap.get(key);
            return value != null ? Integer.parseInt(value) : defaultValue;
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    private long getLong(Map<String, String> configMap, String key, long defaultValue) {
        try {
            String value = configMap.get(key);
            return value != null ? Long.parseLong(value) : defaultValue;
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
}

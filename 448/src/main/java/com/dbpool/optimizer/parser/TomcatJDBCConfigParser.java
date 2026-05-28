package com.dbpool.optimizer.parser;

import com.dbpool.optimizer.model.PoolConfig;
import com.dbpool.optimizer.model.PoolType;
import org.springframework.stereotype.Component;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Properties;

@Component
public class TomcatJDBCConfigParser implements PoolConfigParser {

    @Override
    public PoolConfig parse(Map<String, String> configMap) {
        return PoolConfig.builder()
                .poolType(PoolType.TOMCAT_JDBC)
                .maxPoolSize(getInt(configMap, "maxActive", 100))
                .minIdle(getInt(configMap, "minIdle", 10))
                .connectionTimeoutMs(getLong(configMap, "maxWait", 30000))
                .idleTimeoutMs(getLong(configMap, "minEvictableIdleTimeMillis", 60000))
                .maxLifetimeMs(getLong(configMap, "maxAge", 0))
                .leakDetectionThresholdMs(getLong(configMap, "suspectTimeout", 0) * 1000)
                .validationQuery(configMap.getOrDefault("validationQuery", "SELECT 1"))
                .testOnBorrow(getBoolean(configMap, "testOnBorrow", false))
                .testOnReturn(getBoolean(configMap, "testOnReturn", false))
                .testWhileIdle(getBoolean(configMap, "testWhileIdle", true))
                .timeBetweenEvictionRunsMs(getLong(configMap, "timeBetweenEvictionRunsMillis", 5000))
                .numTestsPerEvictionRun(getInt(configMap, "numTestsPerEvictionRun", 0))
                .build();
    }

    @Override
    public PoolConfig parseProperties(Properties properties) {
        Map<String, String> configMap = new LinkedHashMap<>();
        for (String name : properties.stringPropertyNames()) {
            String key = name.startsWith("spring.datasource.tomcat.")
                    ? name.substring("spring.datasource.tomcat.".length())
                    : name.startsWith("tomcat.jdbc.") ? name.substring("tomcat.jdbc.".length()) : name;
            configMap.put(key, properties.getProperty(name));
        }
        return parse(configMap);
    }

    @Override
    public Map<String, String> exportConfig(PoolConfig config) {
        Map<String, String> configMap = new LinkedHashMap<>();
        configMap.put("spring.datasource.tomcat.maxActive", String.valueOf(config.getMaxPoolSize()));
        configMap.put("spring.datasource.tomcat.minIdle", String.valueOf(config.getMinIdle()));
        configMap.put("spring.datasource.tomcat.maxWait", String.valueOf(config.getConnectionTimeoutMs()));
        configMap.put("spring.datasource.tomcat.minEvictableIdleTimeMillis", String.valueOf(config.getIdleTimeoutMs()));
        configMap.put("spring.datasource.tomcat.maxAge", String.valueOf(config.getMaxLifetimeMs()));
        configMap.put("spring.datasource.tomcat.suspectTimeout", String.valueOf(config.getLeakDetectionThresholdMs() / 1000));
        configMap.put("spring.datasource.tomcat.validationQuery", config.getValidationQuery());
        configMap.put("spring.datasource.tomcat.testOnBorrow", String.valueOf(config.isTestOnBorrow()));
        configMap.put("spring.datasource.tomcat.testOnReturn", String.valueOf(config.isTestOnReturn()));
        configMap.put("spring.datasource.tomcat.testWhileIdle", String.valueOf(config.isTestWhileIdle()));
        configMap.put("spring.datasource.tomcat.timeBetweenEvictionRunsMillis", String.valueOf(config.getTimeBetweenEvictionRunsMs()));
        configMap.put("spring.datasource.tomcat.numTestsPerEvictionRun", String.valueOf(config.getNumTestsPerEvictionRun()));
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
        return "Tomcat JDBC";
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

    private boolean getBoolean(Map<String, String> configMap, String key, boolean defaultValue) {
        String value = configMap.get(key);
        return value != null ? Boolean.parseBoolean(value) : defaultValue;
    }
}

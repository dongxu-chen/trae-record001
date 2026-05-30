package com.hotconfig.core.health;

import com.hotconfig.annotation.ConfigHealthCheck;
import com.hotconfig.annotation.HotConfig;
import com.hotconfig.annotation.HotValue;
import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.convert.TypeConverter;
import com.hotconfig.core.health.ConfigHealthCheckResult.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.regex.Pattern;

public class ConfigHealthChecker {

    private static final Logger logger = LoggerFactory.getLogger(ConfigHealthChecker.class);

    private static volatile ConfigHealthChecker instance;

    private final ConfigManager configManager;
    private final Set<String> referencedKeys = ConcurrentHashMap.newKeySet();
    private final Map<String, FieldReferenceInfo> keyToFieldMap = new ConcurrentHashMap<>();
    private final List<ConfigHealthCheckResult> checkHistory = new CopyOnWriteArrayList<>();

    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1, r -> {
        Thread t = new Thread(r, "config-health-checker");
        t.setDaemon(true);
        return t;
    });

    private ScheduledFuture<?> scheduledCheckFuture;
    private long defaultCheckIntervalMs = 60000;
    private int maxHistorySize = 50;

    private ConfigHealthChecker(ConfigManager configManager) {
        this.configManager = configManager;
    }

    public static ConfigHealthChecker getInstance() {
        if (instance == null) {
            synchronized (ConfigHealthChecker.class) {
                if (instance == null) {
                    instance = new ConfigHealthChecker(ConfigManager.getInstance());
                }
            }
        }
        return instance;
    }

    public static ConfigHealthChecker getInstance(ConfigManager configManager) {
        if (instance == null) {
            synchronized (ConfigHealthChecker.class) {
                if (instance == null) {
                    instance = new ConfigHealthChecker(configManager);
                }
            }
        }
        return instance;
    }

    public void registerConfigBean(Object bean, Class<?> beanClass) {
        HotConfig hotConfig = beanClass.getAnnotation(HotConfig.class);
        if (hotConfig == null) {
            return;
        }

        ConfigHealthCheck healthCheck = beanClass.getAnnotation(ConfigHealthCheck.class);
        if (healthCheck != null && !healthCheck.enabled()) {
            return;
        }

        String prefix = hotConfig.prefix();
        if (!prefix.isEmpty()) {
            prefix = prefix.endsWith(".") ? prefix : prefix + ".";
        }

        for (Field field : beanClass.getDeclaredFields()) {
            HotValue hotValue = field.getAnnotation(HotValue.class);
            if (hotValue == null) {
                continue;
            }

            ConfigHealthCheck fieldHealthCheck = field.getAnnotation(ConfigHealthCheck.class);
            if (fieldHealthCheck != null && !fieldHealthCheck.enabled()) {
                continue;
            }

            String key = hotValue.value();
            String fullKey = prefix + key;

            referencedKeys.add(fullKey);

            FieldReferenceInfo info = new FieldReferenceInfo(
                    fullKey,
                    beanClass.getName(),
                    field.getName(),
                    field.getType(),
                    hotValue.required(),
                    hotValue.defaultValue()
            );
            keyToFieldMap.put(fullKey, info);

            logger.debug("Registered config key reference: {} -> {}.{}",
                    fullKey, beanClass.getName(), field.getName());
        }
    }

    public ConfigHealthCheckResult performFullCheck() {
        return performCheck(true, true, true, true);
    }

    public ConfigHealthCheckResult performCheck(boolean checkDangling, boolean checkRequired,
                                                 boolean checkType, boolean checkUnused) {
        ConfigHealthCheckResult result = new ConfigHealthCheckResult(
                "FullHealthCheck", HealthStatus.HEALTHY);

        result.addMetric("checkStartTime", Instant.now().toString());
        result.addMetric("totalReferencedKeys", referencedKeys.size());
        result.addMetric("totalConfigKeys", configManager.getAllConfig().size());

        Map<String, Object> currentConfig = configManager.getAllConfig();
        Set<String> excludeKeys = new HashSet<>();

        if (checkDangling) {
            checkDanglingReferences(result, currentConfig, excludeKeys);
        }

        if (checkRequired) {
            checkRequiredFields(result, currentConfig, excludeKeys);
        }

        if (checkType) {
            checkTypeCompatibility(result, currentConfig, excludeKeys);
        }

        if (checkUnused) {
            checkUnusedConfig(result, currentConfig, excludeKeys);
        }

        checkDuplicateKeys(result, currentConfig);
        checkFormatErrors(result, currentConfig);

        if (result.hasCriticalIssues()) {
            result = new ConfigHealthCheckResult("FullHealthCheck", HealthStatus.CRITICAL);
        } else if (result.hasHighIssues() || result.getIssueCountBySeverity(IssueSeverity.MEDIUM) > 2) {
            result = new ConfigHealthCheckResult("FullHealthCheck", HealthStatus.WARNING);
        }

        result.addMetric("checkEndTime", Instant.now().toString());
        result.addMetric("totalIssues", result.getIssueCount());

        addToHistory(result);

        logger.info("Health check completed: {}, issues: {}", result.getOverallStatus(), result.getIssueCount());

        return result;
    }

    private void checkDanglingReferences(ConfigHealthCheckResult result,
                                          Map<String, Object> currentConfig,
                                          Set<String> excludeKeys) {
        logger.debug("Checking dangling references...");

        for (Map.Entry<String, FieldReferenceInfo> entry : keyToFieldMap.entrySet()) {
            String key = entry.getKey();
            FieldReferenceInfo info = entry.getValue();

            if (excludeKeys.contains(key)) {
                continue;
            }

            if (!currentConfig.containsKey(key)) {
                String defaultValue = info.getDefaultValue();
                if (defaultValue == null || defaultValue.isEmpty()) {
                    result.addIssue(key,
                            IssueType.DANGLING_REFERENCE,
                            IssueSeverity.HIGH,
                            "Dangling configuration reference detected",
                            String.format("Field '%s.%s' references key '%s' which does not exist in any configuration source and has no default value",
                                    info.getClassName(), info.getFieldName(), key),
                            String.format("Add configuration key '%s' to your config file or environment variables, or provide a defaultValue in @HotValue", key)
                    );
                } else {
                    result.addIssue(key,
                            IssueType.DANGLING_REFERENCE,
                            IssueSeverity.LOW,
                            "Configuration key not found, using default value",
                            String.format("Field '%s.%s' references key '%s' which does not exist in any configuration source. Using default value: '%s'",
                                    info.getClassName(), info.getFieldName(), key, defaultValue),
                            String.format("Consider adding configuration key '%s' to your config file for explicit configuration", key)
                    );
                }
            }
        }

        result.addMetric("danglingReferencesChecked", keyToFieldMap.size());
    }

    private void checkRequiredFields(ConfigHealthCheckResult result,
                                      Map<String, Object> currentConfig,
                                      Set<String> excludeKeys) {
        logger.debug("Checking required fields...");

        for (Map.Entry<String, FieldReferenceInfo> entry : keyToFieldMap.entrySet()) {
            String key = entry.getKey();
            FieldReferenceInfo info = entry.getValue();

            if (excludeKeys.contains(key)) {
                continue;
            }

            if (info.isRequired()) {
                Object value = currentConfig.get(key);
                String defaultValue = info.getDefaultValue();

                if (value == null && (defaultValue == null || defaultValue.isEmpty())) {
                    result.addIssue(key,
                            IssueType.MISSING_REQUIRED,
                            IssueSeverity.CRITICAL,
                            "Required configuration missing",
                            String.format("Field '%s.%s' is marked as required but key '%s' is not present in configuration and has no default value",
                                    info.getClassName(), info.getFieldName(), key),
                            String.format("Add required configuration key '%s' to your configuration", key)
                    );
                } else if (value != null && value.toString().trim().isEmpty()) {
                    result.addIssue(key,
                            IssueType.MISSING_REQUIRED,
                            IssueSeverity.HIGH,
                            "Required configuration is empty",
                            String.format("Field '%s.%s' is marked as required but key '%s' has an empty value",
                                    info.getClassName(), info.getFieldName(), key),
                            String.format("Provide a non-empty value for configuration key '%s'", key)
                    );
                }
            }
        }

        result.addMetric("requiredFieldsChecked",
                (int) keyToFieldMap.values().stream().filter(FieldReferenceInfo::isRequired).count());
    }

    private void checkTypeCompatibility(ConfigHealthCheckResult result,
                                         Map<String, Object> currentConfig,
                                         Set<String> excludeKeys) {
        logger.debug("Checking type compatibility...");

        for (Map.Entry<String, FieldReferenceInfo> entry : keyToFieldMap.entrySet()) {
            String key = entry.getKey();
            FieldReferenceInfo info = entry.getValue();

            if (excludeKeys.contains(key)) {
                continue;
            }

            Object value = currentConfig.get(key);
            if (value == null) {
                continue;
            }

            Class<?> expectedType = info.getFieldType();
            String stringValue = value.toString();

            try {
                TypeConverter.convert(stringValue, expectedType);
            } catch (Exception e) {
                result.addIssue(key,
                        IssueType.TYPE_MISMATCH,
                        IssueSeverity.HIGH,
                        "Type mismatch detected",
                        String.format("Field '%s.%s' expects type '%s' but value '%s' (type: %s) cannot be converted. Error: %s",
                                info.getClassName(), info.getFieldName(),
                                expectedType.getName(), stringValue,
                                value.getClass().getName(), e.getMessage()),
                        String.format("Update configuration key '%s' with a valid %s value", key, expectedType.getSimpleName())
                );
            }
        }

        result.addMetric("typeCompatibilityChecked", keyToFieldMap.size());
    }

    private void checkUnusedConfig(ConfigHealthCheckResult result,
                                    Map<String, Object> currentConfig,
                                    Set<String> excludeKeys) {
        logger.debug("Checking unused configuration keys...");

        List<String> unusedKeys = new ArrayList<>();
        for (String key : currentConfig.keySet()) {
            if (excludeKeys.contains(key)) {
                continue;
            }
            if (!referencedKeys.contains(key) && !isInfrastructureKey(key)) {
                unusedKeys.add(key);
            }
        }

        for (String key : unusedKeys) {
            result.addIssue(key,
                    IssueType.UNUSED_CONFIG,
                    IssueSeverity.LOW,
                    "Unused configuration key",
                    String.format("Configuration key '%s' exists but is not referenced by any @HotConfig bean", key),
                    "Remove this key from configuration if it's no longer needed, or verify the key name is correct"
            );
        }

        result.addMetric("unusedConfigKeys", unusedKeys.size());
    }

    private void checkDuplicateKeys(ConfigHealthCheckResult result, Map<String, Object> currentConfig) {
        Set<String> seenKeys = new HashSet<>();
        Set<String> duplicates = new HashSet<>();

        for (String key : currentConfig.keySet()) {
            String lowerKey = key.toLowerCase();
            if (seenKeys.contains(lowerKey)) {
                duplicates.add(key);
            }
            seenKeys.add(lowerKey);
        }

        for (String key : duplicates) {
            result.addIssue(key,
                    IssueType.DUPLICATE_KEY,
                    IssueSeverity.MEDIUM,
                    "Potential duplicate configuration key",
                    String.format("Configuration key '%s' appears to have duplicates (case-insensitive check)", key),
                    "Review your configuration files and remove duplicate entries"
            );
        }

        result.addMetric("duplicateKeysFound", duplicates.size());
    }

    private void checkFormatErrors(ConfigHealthCheckResult result, Map<String, Object> currentConfig) {
        Pattern placeholderPattern = Pattern.compile("\\$\\{[^}]+\\}");

        for (Map.Entry<String, Object> entry : currentConfig.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();

            if (value instanceof String) {
                String strValue = (String) value;

                if (placeholderPattern.matcher(strValue).find()) {
                    if (!strValue.contains("${") || !strValue.contains("}")) {
                        result.addIssue(key,
                                IssueType.FORMAT_ERROR,
                                IssueSeverity.MEDIUM,
                                "Malformed placeholder detected",
                                String.format("Value '%s' contains malformed placeholder syntax", strValue),
                                "Fix the placeholder syntax: ${placeholder}"
                        );
                    }
                }

                if (strValue.trim().isEmpty() && !strValue.isEmpty()) {
                    result.addIssue(key,
                            IssueType.FORMAT_ERROR,
                            IssueSeverity.LOW,
                            "Value contains only whitespace",
                            String.format("Configuration key '%s' has a value that is only whitespace", key),
                            "Remove the whitespace or set to empty string explicitly"
                    );
                }
            }
        }
    }

    private boolean isInfrastructureKey(String key) {
        return key.startsWith("spring.") ||
                key.startsWith("server.") ||
                key.startsWith("logging.") ||
                key.startsWith("management.") ||
                key.startsWith("apollo.") ||
                key.startsWith("hotconfig.");
    }

    public ConfigHealthCheckResult checkSingleKey(String key) {
        ConfigHealthCheckResult result = new ConfigHealthCheckResult(
                "SingleKeyCheck:" + key, HealthStatus.HEALTHY);

        FieldReferenceInfo info = keyToFieldMap.get(key);
        Map<String, Object> currentConfig = configManager.getAllConfig();

        if (info == null) {
            result.addIssue(key,
                    IssueType.UNUSED_CONFIG,
                    IssueSeverity.LOW,
                    "Key not referenced by any bean",
                    String.format("Configuration key '%s' is not referenced by any @HotConfig bean", key),
                    null
            );
        } else {
            if (!currentConfig.containsKey(key)) {
                result.addIssue(key,
                        IssueType.DANGLING_REFERENCE,
                        IssueSeverity.HIGH,
                        "Dangling reference",
                        String.format("Key '%s' referenced by %s.%s does not exist in configuration",
                                key, info.getClassName(), info.getFieldName()),
                        null
                );
            }

            Object value = currentConfig.get(key);
            if (value != null) {
                try {
                    TypeConverter.convert(value.toString(), info.getFieldType());
                } catch (Exception e) {
                    result.addIssue(key,
                            IssueType.TYPE_MISMATCH,
                            IssueSeverity.HIGH,
                            "Type mismatch",
                            String.format("Cannot convert value '%s' to type %s: %s",
                                    value, info.getFieldType().getName(), e.getMessage()),
                            null
                    );
                }
            }
        }

        addToHistory(result);
        return result;
    }

    public Set<String> getReferencedKeys() {
        return Collections.unmodifiableSet(referencedKeys);
    }

    public Map<String, FieldReferenceInfo> getKeyReferences() {
        return Collections.unmodifiableMap(keyToFieldMap);
    }

    public Set<String> getDanglingKeys() {
        Set<String> dangling = new HashSet<>();
        Map<String, Object> currentConfig = configManager.getAllConfig();

        for (String key : referencedKeys) {
            if (!currentConfig.containsKey(key)) {
                dangling.add(key);
            }
        }
        return dangling;
    }

    public Set<String> getUnusedConfigKeys() {
        Set<String> unused = new HashSet<>();
        Map<String, Object> currentConfig = configManager.getAllConfig();

        for (String key : currentConfig.keySet()) {
            if (!referencedKeys.contains(key) && !isInfrastructureKey(key)) {
                unused.add(key);
            }
        }
        return unused;
    }

    public void startScheduledCheck() {
        startScheduledCheck(defaultCheckIntervalMs);
    }

    public void startScheduledCheck(long intervalMs) {
        if (scheduledCheckFuture != null && !scheduledCheckFuture.isDone()) {
            scheduledCheckFuture.cancel(false);
        }

        scheduledCheckFuture = scheduler.scheduleAtFixedRate(() -> {
            try {
                performFullCheck();
            } catch (Exception e) {
                logger.error("Scheduled health check failed", e);
            }
        }, intervalMs, intervalMs, TimeUnit.MILLISECONDS);

        logger.info("Scheduled health check started with interval: {}ms", intervalMs);
    }

    public void stopScheduledCheck() {
        if (scheduledCheckFuture != null) {
            scheduledCheckFuture.cancel(false);
            scheduledCheckFuture = null;
            logger.info("Scheduled health check stopped");
        }
    }

    private synchronized void addToHistory(ConfigHealthCheckResult result) {
        checkHistory.add(result);
        while (checkHistory.size() > maxHistorySize) {
            checkHistory.remove(0);
        }
    }

    public List<ConfigHealthCheckResult> getCheckHistory() {
        return new ArrayList<>(checkHistory);
    }

    public ConfigHealthCheckResult getLatestCheckResult() {
        if (checkHistory.isEmpty()) {
            return null;
        }
        return checkHistory.get(checkHistory.size() - 1);
    }

    public List<ConfigHealthCheckResult> getCheckHistoryByStatus(HealthStatus status) {
        List<ConfigHealthCheckResult> result = new ArrayList<>();
        for (ConfigHealthCheckResult check : checkHistory) {
            if (check.getOverallStatus() == status) {
                result.add(check);
            }
        }
        return result;
    }

    public long getDefaultCheckIntervalMs() {
        return defaultCheckIntervalMs;
    }

    public void setDefaultCheckIntervalMs(long defaultCheckIntervalMs) {
        this.defaultCheckIntervalMs = defaultCheckIntervalMs;
    }

    public int getMaxHistorySize() {
        return maxHistorySize;
    }

    public void setMaxHistorySize(int maxHistorySize) {
        this.maxHistorySize = maxHistorySize;
    }

    public void destroy() {
        stopScheduledCheck();
        scheduler.shutdown();
        checkHistory.clear();
        referencedKeys.clear();
        keyToFieldMap.clear();
    }

    public static class FieldReferenceInfo {
        private final String key;
        private final String className;
        private final String fieldName;
        private final Class<?> fieldType;
        private final boolean required;
        private final String defaultValue;

        public FieldReferenceInfo(String key, String className, String fieldName,
                                   Class<?> fieldType, boolean required, String defaultValue) {
            this.key = key;
            this.className = className;
            this.fieldName = fieldName;
            this.fieldType = fieldType;
            this.required = required;
            this.defaultValue = defaultValue;
        }

        public String getKey() {
            return key;
        }

        public String getClassName() {
            return className;
        }

        public String getFieldName() {
            return fieldName;
        }

        public Class<?> getFieldType() {
            return fieldType;
        }

        public boolean isRequired() {
            return required;
        }

        public String getDefaultValue() {
            return defaultValue;
        }

        @Override
        public String toString() {
            return className + "." + fieldName + " (" + fieldType.getName() + ")";
        }
    }
}

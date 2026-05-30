package com.hotconfig.core.diff;

import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.event.ConfigChange;
import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.listener.ConfigChangeListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

public class ConfigDiffManager {

    private static final Logger logger = LoggerFactory.getLogger(ConfigDiffManager.class);

    private static volatile ConfigDiffManager instance;

    private final ConfigManager configManager;
    private final List<ConfigDiffListener> diffListeners = new CopyOnWriteArrayList<>();
    private final Map<String, ConfigDiff> diffHistory = new LinkedHashMap<String, ConfigDiff>() {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, ConfigDiff> eldest) {
            return size() > maxHistorySize;
        }
    };

    private final ExecutorService asyncExecutor = Executors.newFixedThreadPool(2, r -> {
        Thread t = new Thread(r, "config-diff-notifier");
        t.setDaemon(true);
        return t;
    });

    private final AtomicBoolean notifyInProgress = new AtomicBoolean(false);

    private int maxHistorySize = 100;
    private boolean asyncNotification = true;

    private ConfigDiffManager(ConfigManager configManager) {
        this.configManager = configManager;
    }

    public static ConfigDiffManager getInstance() {
        if (instance == null) {
            synchronized (ConfigDiffManager.class) {
                if (instance == null) {
                    instance = new ConfigDiffManager(ConfigManager.getInstance());
                }
            }
        }
        return instance;
    }

    public static ConfigDiffManager getInstance(ConfigManager configManager) {
        if (instance == null) {
            synchronized (ConfigDiffManager.class) {
                if (instance == null) {
                    instance = new ConfigDiffManager(configManager);
                }
            }
        }
        return instance;
    }

    public void addDiffListener(ConfigDiffListener listener) {
        if (listener != null) {
            diffListeners.add(listener);
            logger.info("Added config diff listener: {}", listener.getClass().getName());
        }
    }

    public void removeDiffListener(ConfigDiffListener listener) {
        diffListeners.remove(listener);
        logger.info("Removed config diff listener: {}", listener.getClass().getName());
    }

    public ConfigDiff createAndNotifyDiff(String sourceName,
                                           Map<String, ConfigChange> changes,
                                           Map<String, Object> beforeValues,
                                           Map<String, Object> afterValues) {
        ConfigDiff diff = new ConfigDiff(sourceName, changes, beforeValues, afterValues);
        notifyDiff(diff);
        return diff;
    }

    public ConfigDiff createAndNotifyDiffFromChanges(String sourceName,
                                                      Map<String, ConfigChange> changes) {
        ConfigDiff diff = ConfigDiff.fromChanges(sourceName, changes);
        notifyDiff(diff);
        return diff;
    }

    public ConfigDiff createAndNotifyDiffFromCompare(String sourceName,
                                                      Map<String, Object> before,
                                                      Map<String, Object> after) {
        ConfigDiff diff = ConfigDiff.compare(sourceName, before, after);
        notifyDiff(diff);
        return diff;
    }

    public void notifyDiff(ConfigDiff diff) {
        if (diff == null || !diff.hasChanges()) {
            return;
        }

        String diffId = generateDiffId(diff);
        diffHistory.put(diffId, diff);

        logger.info("Config diff created: {} changes from '{}'", diff.getChangeCount(), diff.getSourceName());
        logger.debug("Diff details:\n{}", diff.getFormattedDiff());

        if (asyncNotification) {
            asyncExecutor.submit(() -> notifyListeners(diff));
        } else {
            notifyListeners(diff);
        }
    }

    private void notifyListeners(ConfigDiff diff) {
        if (!notifyInProgress.compareAndSet(false, true)) {
            logger.debug("Notification already in progress, skipping duplicate");
            return;
        }

        try {
            for (ConfigDiffListener listener : diffListeners) {
                try {
                    listener.onConfigDiff(diff);
                } catch (Exception e) {
                    logger.error("Error in config diff listener: {}", listener.getClass().getName(), e);
                }
            }
        } finally {
            notifyInProgress.set(false);
        }
    }

    public CompletableFuture<ConfigDiff> notifyDiffAsync(ConfigDiff diff) {
        if (diff == null || !diff.hasChanges()) {
            return CompletableFuture.completedFuture(null);
        }

        String diffId = generateDiffId(diff);
        diffHistory.put(diffId, diff);

        return CompletableFuture.supplyAsync(() -> {
            notifyListeners(diff);
            return diff;
        }, asyncExecutor);
    }

    public ConfigDiffListener createLoggingDiffListener() {
        return diff -> {
            logger.info("=== Configuration Change Notification ===");
            for (String line : diff.getSummary()) {
                logger.info(line);
            }
        };
    }

    public ConfigDiffListener createSlackNotifier(String webhookUrl) {
        return diff -> {
            try {
                StringBuilder payload = new StringBuilder();
                payload.append("{\"text\":\"*Configuration Change Notification*\\n\\n");
                for (String line : diff.getSummary()) {
                    payload.append(line).append("\\n");
                }
                payload.append("\"}");

                logger.info("Would send Slack notification to {}: {}", webhookUrl, payload);
            } catch (Exception e) {
                logger.error("Failed to send Slack notification", e);
            }
        };
    }

    public ConfigDiffListener createEmailNotifier(String from, String to, String subjectPrefix) {
        return diff -> {
            try {
                StringBuilder body = new StringBuilder();
                body.append("Configuration Change Notification\n\n");
                body.append("Source: ").append(diff.getSourceName()).append("\n");
                body.append("Timestamp: ").append(new Date(diff.getTimestamp())).append("\n\n");
                for (String line : diff.getSummary()) {
                    body.append(line).append("\n");
                }

                logger.info("Would send email from {} to {} with subject [{}] Config Change:\n{}",
                        from, to, subjectPrefix, body);
            } catch (Exception e) {
                logger.error("Failed to send email notification", e);
            }
        };
    }

    public ConfigDiffListener createWebhookNotifier(String url, Map<String, String> headers) {
        return diff -> {
            try {
                logger.info("Would send webhook to {} with headers {}: \n{}",
                        url, headers, diff.getFormattedDiff());
            } catch (Exception e) {
                logger.error("Failed to send webhook notification", e);
            }
        };
    }

    public void registerAsConfigChangeListener() {
        configManager.addConfigChangeListener(new ConfigChangeListener() {
            @Override
            public void onChange(ConfigChangeEvent event) {
                createAndNotifyDiffFromChanges(event.getSource(), event.getChanges());
            }
        });
    }

    private String generateDiffId(ConfigDiff diff) {
        return diff.getSourceName() + "-" + diff.getTimestamp() + "-" + UUID.randomUUID().toString().substring(0, 8);
    }

    public List<ConfigDiff> getDiffHistory() {
        return new ArrayList<>(diffHistory.values());
    }

    public List<ConfigDiff> getDiffHistoryBySource(String sourceName) {
        List<ConfigDiff> result = new ArrayList<>();
        for (ConfigDiff diff : diffHistory.values()) {
            if (diff.getSourceName().equals(sourceName)) {
                result.add(diff);
            }
        }
        return result;
    }

    public List<ConfigDiff> getDiffHistoryByKey(String key) {
        List<ConfigDiff> result = new ArrayList<>();
        for (ConfigDiff diff : diffHistory.values()) {
            if (diff.hasChange(key)) {
                result.add(diff);
            }
        }
        return result;
    }

    public List<ConfigDiff> getDiffHistory(long startTime, long endTime) {
        List<ConfigDiff> result = new ArrayList<>();
        for (ConfigDiff diff : diffHistory.values()) {
            if (diff.getTimestamp() >= startTime && diff.getTimestamp() <= endTime) {
                result.add(diff);
            }
        }
        return result;
    }

    public ConfigDiff getLatestDiff() {
        if (diffHistory.isEmpty()) {
            return null;
        }
        List<ConfigDiff> diffs = new ArrayList<>(diffHistory.values());
        return diffs.get(diffs.size() - 1);
    }

    public Map<String, Object> getValueHistory(String key) {
        Map<String, Object> history = new LinkedHashMap<>();
        for (ConfigDiff diff : diffHistory.values()) {
            if (diff.hasChange(key)) {
                history.put(diff.getSourceName() + "@" + diff.getTimestamp(),
                        diff.getChange(key).getNewValue());
            }
        }
        return history;
    }

    public Map<String, List<ConfigChange.ChangeType>> getChangeTypeHistory() {
        Map<String, List<ConfigChange.ChangeType>> history = new LinkedHashMap<>();
        for (ConfigDiff diff : diffHistory.values()) {
            for (Map.Entry<String, ConfigChange> entry : diff.getChanges().entrySet()) {
                history.computeIfAbsent(entry.getKey(), k -> new ArrayList<>())
                        .add(entry.getValue().getChangeType());
            }
        }
        return history;
    }

    public Map<String, Object> getCurrentState() {
        return configManager.getAllConfig();
    }

    public void clearHistory() {
        diffHistory.clear();
    }

    public int getMaxHistorySize() {
        return maxHistorySize;
    }

    public void setMaxHistorySize(int maxHistorySize) {
        this.maxHistorySize = maxHistorySize;
    }

    public boolean isAsyncNotification() {
        return asyncNotification;
    }

    public void setAsyncNotification(boolean asyncNotification) {
        this.asyncNotification = asyncNotification;
    }

    public void destroy() {
        asyncExecutor.shutdown();
        diffListeners.clear();
        clearHistory();
    }
}

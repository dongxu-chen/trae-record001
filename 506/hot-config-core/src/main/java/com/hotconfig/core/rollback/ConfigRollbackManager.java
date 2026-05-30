package com.hotconfig.core.rollback;

import com.hotconfig.annotation.ConfigRollback;
import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.event.ConfigChange;
import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.listener.ConfigChangeListener;
import com.hotconfig.core.refresh.BeanPropertyRefresher;
import com.hotconfig.core.source.ConfigSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.ReentrantLock;

public class ConfigRollbackManager {

    private static final Logger logger = LoggerFactory.getLogger(ConfigRollbackManager.class);

    private static volatile ConfigRollbackManager instance;

    private final ConfigManager configManager;
    private final BeanPropertyRefresher propertyRefresher;

    private final Deque<ConfigSnapshot> snapshotHistory = new LinkedList<>();
    private final Map<String, ConfigSnapshot> snapshotIndex = new ConcurrentHashMap<>();
    private final Map<String, RollbackTask> pendingRollbacks = new ConcurrentHashMap<>();

    private final ReentrantLock rollbackLock = new ReentrantLock();
    private final AtomicBoolean rollbackInProgress = new AtomicBoolean(false);

    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1, r -> {
        Thread t = new Thread(r, "config-rollback-scheduler");
        t.setDaemon(true);
        return t;
    });

    private int maxHistorySize = 50;
    private long defaultRollbackTimeoutMs = 30000;

    private ConfigRollbackManager(ConfigManager configManager, BeanPropertyRefresher propertyRefresher) {
        this.configManager = configManager;
        this.propertyRefresher = propertyRefresher;
    }

    public static ConfigRollbackManager getInstance() {
        if (instance == null) {
            synchronized (ConfigRollbackManager.class) {
                if (instance == null) {
                    instance = new ConfigRollbackManager(ConfigManager.getInstance(),
                            new BeanPropertyRefresher());
                }
            }
        }
        return instance;
    }

    public static ConfigRollbackManager getInstance(ConfigManager configManager,
                                                    BeanPropertyRefresher propertyRefresher) {
        if (instance == null) {
            synchronized (ConfigRollbackManager.class) {
                if (instance == null) {
                    instance = new ConfigRollbackManager(configManager, propertyRefresher);
                }
            }
        }
        return instance;
    }

    public ConfigSnapshot createSnapshot(String sourceName, String description) {
        return createSnapshot(sourceName, null, ConfigSnapshot.SnapshotType.MANUAL, description);
    }

    public ConfigSnapshot createSnapshotBeforeChange(String sourceName, Map<String, ConfigChange> changes) {
        return createSnapshot(sourceName, changes, ConfigSnapshot.SnapshotType.AUTO_BEFORE_CHANGE,
                "Before config change");
    }

    public ConfigSnapshot createSnapshotAfterChange(String sourceName, Map<String, ConfigChange> changes) {
        return createSnapshot(sourceName, changes, ConfigSnapshot.SnapshotType.AUTO_AFTER_CHANGE,
                "After config change");
    }

    private ConfigSnapshot createSnapshot(String sourceName, Map<String, ConfigChange> changes,
                                           ConfigSnapshot.SnapshotType type, String description) {
        Map<String, Object> configValues = configManager.getAllConfig();
        ConfigSnapshot snapshot = new ConfigSnapshot(sourceName, configValues,
                changes != null ? changes : Collections.emptyMap(), type, description);

        addSnapshotToHistory(snapshot);

        logger.info("Created config snapshot: {}, type: {}, size: {} properties",
                snapshot.getId(), type, snapshot.size());

        return snapshot;
    }

    private synchronized void addSnapshotToHistory(ConfigSnapshot snapshot) {
        snapshotHistory.addFirst(snapshot);
        snapshotIndex.put(snapshot.getId(), snapshot);

        while (snapshotHistory.size() > maxHistorySize) {
            ConfigSnapshot removed = snapshotHistory.removeLast();
            snapshotIndex.remove(removed.getId());
            logger.debug("Removed old snapshot: {}", removed.getId());
        }
    }

    public RollbackResult rollbackToSnapshot(String snapshotId) {
        return rollbackToSnapshot(snapshotId, defaultRollbackTimeoutMs);
    }

    public RollbackResult rollbackToSnapshot(String snapshotId, long timeoutMs) {
        ConfigSnapshot snapshot = snapshotIndex.get(snapshotId);
        if (snapshot == null) {
            return RollbackResult.failure("Snapshot not found: " + snapshotId);
        }

        return doRollback(snapshot, timeoutMs, null);
    }

    public RollbackResult rollbackToPrevious() {
        if (snapshotHistory.size() < 2) {
            return RollbackResult.failure("No previous snapshot available");
        }

        Iterator<ConfigSnapshot> iterator = snapshotHistory.iterator();
        iterator.next();
        ConfigSnapshot previous = iterator.next();

        return doRollback(previous, defaultRollbackTimeoutMs, null);
    }

    public RollbackResult rollbackToTimestamp(Instant timestamp) {
        ConfigSnapshot target = null;
        for (ConfigSnapshot snapshot : snapshotHistory) {
            if (!snapshot.getTimestamp().isAfter(timestamp)) {
                target = snapshot;
                break;
            }
        }

        if (target == null) {
            return RollbackResult.failure("No snapshot found before timestamp: " + timestamp);
        }

        return doRollback(target, defaultRollbackTimeoutMs, null);
    }

    public RollbackResult rollbackByKeys(Set<String> keys, String snapshotId) {
        ConfigSnapshot snapshot = snapshotIndex.get(snapshotId);
        if (snapshot == null) {
            return RollbackResult.failure("Snapshot not found: " + snapshotId);
        }

        return doRollback(snapshot, defaultRollbackTimeoutMs, keys);
    }

    private RollbackResult doRollback(ConfigSnapshot snapshot, long timeoutMs, Set<String> keysToRollback) {
        if (!rollbackInProgress.compareAndSet(false, true)) {
            return RollbackResult.failure("Rollback already in progress");
        }

        rollbackLock.lock();
        try {
            logger.info("Starting rollback to snapshot: {}, keys: {}", snapshot.getId(), keysToRollback);

            ConfigSnapshot beforeRollback = createSnapshot(configManager.getConfigSources().get(0).getName(),
                    Collections.emptyMap(), ConfigSnapshot.SnapshotType.AUTO_ROLLBACK,
                    "Before rollback to " + snapshot.getId());

            Map<String, Object> targetValues = snapshot.getConfigValues();
            Map<String, ConfigChange> rollbackChanges = new HashMap<>();
            Map<String, Object> currentValues = configManager.getAllConfig();

            Set<String> keys = keysToRollback != null ? keysToRollback : targetValues.keySet();

            for (String key : keys) {
                if (!targetValues.containsKey(key)) {
                    continue;
                }

                Object oldValue = currentValues.get(key);
                Object newValue = targetValues.get(key);

                if (!Objects.equals(oldValue, newValue)) {
                    ConfigChange.ChangeType changeType;
                    if (oldValue == null) {
                        changeType = ConfigChange.ChangeType.ADDED;
                    } else if (newValue == null) {
                        changeType = ConfigChange.ChangeType.DELETED;
                    } else {
                        changeType = ConfigChange.ChangeType.MODIFIED;
                    }

                    rollbackChanges.put(key, new ConfigChange(key, oldValue, newValue, changeType));
                    configManager.setLocalValue(key, newValue);
                }
            }

            if (!rollbackChanges.isEmpty()) {
                propertyRefresher.refreshAllBeans();

                ConfigChangeEvent event = new ConfigChangeEvent(
                        "rollback", rollbackChanges, this);

                for (ConfigSource source : configManager.getConfigSources()) {
                    source.fireChangeEvent(event);
                }

                createSnapshot(configManager.getConfigSources().get(0).getName(),
                        rollbackChanges, ConfigSnapshot.SnapshotType.AUTO_ROLLBACK,
                        "After rollback from " + beforeRollback.getId() + " to " + snapshot.getId());

                logger.info("Rollback completed successfully, {} keys changed", rollbackChanges.size());
                return RollbackResult.success(snapshot.getId(), rollbackChanges, beforeRollback.getId());
            } else {
                logger.info("Rollback completed, no changes needed");
                return RollbackResult.noChanges(snapshot.getId());
            }

        } catch (Exception e) {
            logger.error("Rollback failed", e);
            return RollbackResult.failure("Rollback failed: " + e.getMessage());
        } finally {
            rollbackLock.unlock();
            rollbackInProgress.set(false);
        }
    }

    public String scheduleRollback(String snapshotId, long delayMs, ConfigRollback rollbackConfig) {
        String taskId = UUID.randomUUID().toString();

        RollbackTask task = new RollbackTask(taskId, snapshotId, delayMs, rollbackConfig);

        ScheduledFuture<?> future = scheduler.schedule(() -> {
            try {
                RollbackResult result = rollbackToSnapshot(snapshotId);
                task.setResult(result);
                if (!result.isSuccess() && rollbackConfig != null) {
                    retryRollback(task);
                }
            } catch (Exception e) {
                logger.error("Scheduled rollback failed", e);
                task.setResult(RollbackResult.failure("Scheduled rollback failed: " + e.getMessage()));
            } finally {
                pendingRollbacks.remove(taskId);
            }
        }, delayMs, TimeUnit.MILLISECONDS);

        task.setFuture(future);
        pendingRollbacks.put(taskId, task);

        logger.info("Scheduled rollback task: {}, snapshot: {}, delay: {}ms", taskId, snapshotId, delayMs);
        return taskId;
    }

    private void retryRollback(RollbackTask task) {
        ConfigRollback config = task.getRollbackConfig();
        if (config == null) {
            return;
        }

        int maxAttempts = config.maxRetryAttempts();
        long delayMs = config.retryDelayMs();

        while (task.getRetryCount() < maxAttempts && !task.getResult().isSuccess()) {
            try {
                Thread.sleep(delayMs);

                task.incrementRetryCount();
                logger.info("Retrying rollback (attempt {}/{}), task: {}",
                        task.getRetryCount(), maxAttempts, task.getTaskId());

                RollbackResult result = rollbackToSnapshot(task.getSnapshotId());
                task.setResult(result);

                if (result.isSuccess()) {
                    break;
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                logger.error("Retry rollback failed, task: {}", task.getTaskId(), e);
            }
        }
    }

    public boolean cancelRollback(String taskId) {
        RollbackTask task = pendingRollbacks.remove(taskId);
        if (task != null && task.getFuture() != null) {
            boolean cancelled = task.getFuture().cancel(false);
            logger.info("Cancelled rollback task: {}, cancelled: {}", taskId, cancelled);
            return cancelled;
        }
        return false;
    }

    public void validateAndRollbackOnError(Runnable operation, String snapshotId) {
        ConfigSnapshot snapshot = createSnapshotBeforeChange("validation", Collections.emptyMap());

        try {
            operation.run();
        } catch (Exception e) {
            logger.error("Operation failed, triggering auto-rollback", e);
            rollbackToSnapshot(snapshot.getId());
            throw e;
        }
    }

    public List<ConfigSnapshot> getSnapshotHistory() {
        return new ArrayList<>(snapshotHistory);
    }

    public ConfigSnapshot getSnapshot(String snapshotId) {
        return snapshotIndex.get(snapshotId);
    }

    public List<ConfigSnapshot> getSnapshotsByType(ConfigSnapshot.SnapshotType type) {
        List<ConfigSnapshot> result = new ArrayList<>();
        for (ConfigSnapshot snapshot : snapshotHistory) {
            if (snapshot.getType() == type) {
                result.add(snapshot);
            }
        }
        return result;
    }

    public List<ConfigSnapshot> getSnapshotsBySource(String sourceName) {
        List<ConfigSnapshot> result = new ArrayList<>();
        for (ConfigSnapshot snapshot : snapshotHistory) {
            if (snapshot.getSourceName().equals(sourceName)) {
                result.add(snapshot);
            }
        }
        return result;
    }

    public List<RollbackTask> getPendingRollbacks() {
        return new ArrayList<>(pendingRollbacks.values());
    }

    public void setMaxHistorySize(int maxHistorySize) {
        this.maxHistorySize = maxHistorySize;
    }

    public int getMaxHistorySize() {
        return maxHistorySize;
    }

    public void setDefaultRollbackTimeoutMs(long defaultRollbackTimeoutMs) {
        this.defaultRollbackTimeoutMs = defaultRollbackTimeoutMs;
    }

    public long getDefaultRollbackTimeoutMs() {
        return defaultRollbackTimeoutMs;
    }

    public boolean isRollbackInProgress() {
        return rollbackInProgress.get();
    }

    public void clearHistory() {
        snapshotHistory.clear();
        snapshotIndex.clear();
    }

    public void destroy() {
        scheduler.shutdown();
        clearHistory();
        pendingRollbacks.clear();
    }

    public static class RollbackTask {
        private final String taskId;
        private final String snapshotId;
        private final long delayMs;
        private final ConfigRollback rollbackConfig;
        private ScheduledFuture<?> future;
        private RollbackResult result;
        private int retryCount = 0;

        public RollbackTask(String taskId, String snapshotId, long delayMs, ConfigRollback rollbackConfig) {
            this.taskId = taskId;
            this.snapshotId = snapshotId;
            this.delayMs = delayMs;
            this.rollbackConfig = rollbackConfig;
        }

        public String getTaskId() {
            return taskId;
        }

        public String getSnapshotId() {
            return snapshotId;
        }

        public long getDelayMs() {
            return delayMs;
        }

        public ConfigRollback getRollbackConfig() {
            return rollbackConfig;
        }

        public ScheduledFuture<?> getFuture() {
            return future;
        }

        public void setFuture(ScheduledFuture<?> future) {
            this.future = future;
        }

        public RollbackResult getResult() {
            return result;
        }

        public void setResult(RollbackResult result) {
            this.result = result;
        }

        public int getRetryCount() {
            return retryCount;
        }

        public void incrementRetryCount() {
            this.retryCount++;
        }
    }

    public static class RollbackResult {
        private final boolean success;
        private final boolean hasChanges;
        private final String message;
        private final String targetSnapshotId;
        private final String beforeRollbackSnapshotId;
        private final Map<String, ConfigChange> changes;
        private final Instant timestamp;

        private RollbackResult(boolean success, boolean hasChanges, String message,
                                String targetSnapshotId, String beforeRollbackSnapshotId,
                                Map<String, ConfigChange> changes) {
            this.success = success;
            this.hasChanges = hasChanges;
            this.message = message;
            this.targetSnapshotId = targetSnapshotId;
            this.beforeRollbackSnapshotId = beforeRollbackSnapshotId;
            this.changes = changes != null ? Collections.unmodifiableMap(changes) : Collections.emptyMap();
            this.timestamp = Instant.now();
        }

        public static RollbackResult success(String targetSnapshotId, Map<String, ConfigChange> changes,
                                              String beforeRollbackSnapshotId) {
            return new RollbackResult(true, true, "Rollback successful",
                    targetSnapshotId, beforeRollbackSnapshotId, changes);
        }

        public static RollbackResult noChanges(String targetSnapshotId) {
            return new RollbackResult(true, false, "No changes needed for rollback",
                    targetSnapshotId, null, Collections.emptyMap());
        }

        public static RollbackResult failure(String message) {
            return new RollbackResult(false, false, message, null, null, null);
        }

        public boolean isSuccess() {
            return success;
        }

        public boolean hasChanges() {
            return hasChanges;
        }

        public String getMessage() {
            return message;
        }

        public String getTargetSnapshotId() {
            return targetSnapshotId;
        }

        public String getBeforeRollbackSnapshotId() {
            return beforeRollbackSnapshotId;
        }

        public Map<String, ConfigChange> getChanges() {
            return changes;
        }

        public Instant getTimestamp() {
            return timestamp;
        }

        @Override
        public String toString() {
            return "RollbackResult{" +
                    "success=" + success +
                    ", hasChanges=" + hasChanges +
                    ", message='" + message + '\'' +
                    ", targetSnapshotId='" + targetSnapshotId + '\'' +
                    ", changes=" + changes.size() +
                    '}';
        }
    }
}

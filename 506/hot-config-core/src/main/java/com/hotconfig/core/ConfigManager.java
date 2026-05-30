package com.hotconfig.core;

import com.hotconfig.annotation.ConfigRollback;
import com.hotconfig.core.convert.TypeConverter;
import com.hotconfig.core.diff.ConfigDiffManager;
import com.hotconfig.core.event.ConfigChange;
import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.listener.ConfigChangeListener;
import com.hotconfig.core.rollback.ConfigRollbackManager;
import com.hotconfig.core.rollback.ConfigSnapshot;
import com.hotconfig.core.source.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Type;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

public class ConfigManager {

    private static final Logger logger = LoggerFactory.getLogger(ConfigManager.class);

    private static volatile ConfigManager instance;

    private final CompositeConfigSource compositeSource;

    private final Map<String, Object> localCache = new ConcurrentHashMap<>();

    private final AtomicBoolean initialized = new AtomicBoolean(false);

    private final List<ConfigChangeListener> globalListeners = new ArrayList<>();

    private ConfigRollbackManager rollbackManager;
    private ConfigDiffManager diffManager;

    private final AtomicBoolean rollbackEnabled = new AtomicBoolean(true);
    private final AtomicBoolean diffNotificationEnabled = new AtomicBoolean(true);

    private ConfigManager() {
        this.compositeSource = new CompositeConfigSource();
        this.compositeSource.addChangeListener(this::onConfigChange);
    }

    public static ConfigManager getInstance() {
        if (instance == null) {
            synchronized (ConfigManager.class) {
                if (instance == null) {
                    instance = new ConfigManager();
                }
            }
        }
        return instance;
    }

    public void init() {
        if (initialized.compareAndSet(false, true)) {
            logger.info("Initializing ConfigManager...");

            addDefaultSources();

            compositeSource.init();

            initRollbackManager();
            initDiffManager();

            logger.info("ConfigManager initialized successfully with {} config sources",
                    compositeSource.getSources().size());
        }
    }

    private void initRollbackManager() {
        if (rollbackManager == null) {
            rollbackManager = ConfigRollbackManager.getInstance(this, null);
            logger.info("ConfigRollbackManager initialized");
        }
    }

    private void initDiffManager() {
        if (diffManager == null) {
            diffManager = ConfigDiffManager.getInstance(this);
            diffManager.addDiffListener(diffManager.createLoggingDiffListener());
            logger.info("ConfigDiffManager initialized with logging listener");
        }
    }

    private void addDefaultSources() {
        EnvironmentConfigSource envSource = new EnvironmentConfigSource();
        compositeSource.addSource(envSource);
        logger.debug("Added default config source: {}", envSource.getName());
    }

    public void addConfigSource(ConfigSource source) {
        compositeSource.addSource(source);
        if (initialized.get()) {
            source.init();
        }
    }

    public void removeConfigSource(ConfigSource source) {
        compositeSource.removeSource(source);
        source.destroy();
    }

    public List<ConfigSource> getConfigSources() {
        return compositeSource.getSources();
    }

    public Object getValue(String key) {
        checkInitialized();
        return compositeSource.getValue(key);
    }

    @SuppressWarnings("unchecked")
    public <T> T getValue(String key, Type type) {
        Object value = getValue(key);
        return TypeConverter.convert(value, type);
    }

    @SuppressWarnings("unchecked")
    public <T> T getValue(String key, Type type, String defaultValue) {
        Object value = getValue(key);
        return TypeConverter.convert(value, type, defaultValue);
    }

    @SuppressWarnings("unchecked")
    public <T> T getValue(String key, Class<T> type) {
        Object value = getValue(key);
        return TypeConverter.convert(value, type);
    }

    @SuppressWarnings("unchecked")
    public <T> T getValue(String key, Class<T> type, String defaultValue) {
        Object value = getValue(key);
        return TypeConverter.convert(value, type, defaultValue);
    }

    public String getString(String key) {
        return getValue(key, String.class);
    }

    public String getString(String key, String defaultValue) {
        return getValue(key, String.class, defaultValue);
    }

    public Integer getInt(String key) {
        return getValue(key, Integer.class);
    }

    public Integer getInt(String key, Integer defaultValue) {
        return getValue(key, Integer.class, String.valueOf(defaultValue));
    }

    public Long getLong(String key) {
        return getValue(key, Long.class);
    }

    public Long getLong(String key, Long defaultValue) {
        return getValue(key, Long.class, String.valueOf(defaultValue));
    }

    public Double getDouble(String key) {
        return getValue(key, Double.class);
    }

    public Double getDouble(String key, Double defaultValue) {
        return getValue(key, Double.class, String.valueOf(defaultValue));
    }

    public Boolean getBoolean(String key) {
        return getValue(key, Boolean.class);
    }

    public Boolean getBoolean(String key, Boolean defaultValue) {
        return getValue(key, Boolean.class, String.valueOf(defaultValue));
    }

    public List<String> getList(String key) {
        return getValue(key, List.class);
    }

    public Map<String, Object> getAllConfig() {
        checkInitialized();
        return compositeSource.getAllConfig();
    }

    public Set<String> getPropertyNames() {
        checkInitialized();
        return compositeSource.getPropertyNames();
    }

    public boolean containsKey(String key) {
        checkInitialized();
        return compositeSource.containsKey(key);
    }

    public void addGlobalListener(ConfigChangeListener listener) {
        if (listener != null && !globalListeners.contains(listener)) {
            globalListeners.add(listener);
            compositeSource.addChangeListener(listener);
        }
    }

    public void removeGlobalListener(ConfigChangeListener listener) {
        if (listener != null) {
            globalListeners.remove(listener);
            compositeSource.removeChangeListener(listener);
        }
    }

    public void addListener(String key, ConfigChangeListener listener) {
        compositeSource.addChangeListener(new ConfigChangeListener.KeyBasedListener(key) {
            @Override
            public void onChange(ConfigChangeEvent event) {
                listener.onChange(event);
            }
        });
    }

    public void addListener(String[] keys, ConfigChangeListener listener) {
        compositeSource.addChangeListener(new ConfigChangeListener.KeyBasedListener(keys) {
            @Override
            public void onChange(ConfigChangeEvent event) {
                listener.onChange(event);
            }
        });
    }

    public void addPrefixListener(String prefix, ConfigChangeListener listener) {
        compositeSource.addChangeListener(new ConfigChangeListener.PrefixBasedListener(prefix) {
            @Override
            public void onChange(ConfigChangeEvent event) {
                listener.onChange(event);
            }
        });
    }

    public void addPrefixListener(String[] prefixes, ConfigChangeListener listener) {
        compositeSource.addChangeListener(new ConfigChangeListener.PrefixBasedListener(prefixes) {
            @Override
            public void onChange(ConfigChangeEvent event) {
                listener.onChange(event);
            }
        });
    }

    private void onConfigChange(ConfigChangeEvent event) {
        logger.info("Config changed from source: {}, changed keys: {}",
                event.getSourceName(), event.getChangedKeys());

        Map<String, ConfigChange> changes = new HashMap<>();
        for (Map.Entry<String, com.hotconfig.core.event.ConfigChange> entry : event.getChanges().entrySet()) {
            String key = entry.getKey();
            com.hotconfig.core.event.ConfigChange change = entry.getValue();
            changes.put(key, change);

            switch (change.getChangeType()) {
                case ADDED:
                case MODIFIED:
                    localCache.put(key, change.getNewValue());
                    break;
                case DELETED:
                    localCache.remove(key);
                    break;
            }
        }

        if (rollbackEnabled.get() && rollbackManager != null) {
            rollbackManager.createSnapshotBeforeChange(event.getSourceName(), changes);
        }

        if (diffNotificationEnabled.get() && diffManager != null) {
            diffManager.createAndNotifyDiffFromChanges(event.getSourceName(), changes);
        }
    }

    public void refresh() {
        checkInitialized();
        compositeSource.refreshAll();
        logger.info("ConfigManager refreshed");
    }

    public void destroy() {
        if (initialized.compareAndSet(true, false)) {
            compositeSource.destroy();
            localCache.clear();
            globalListeners.clear();
            logger.info("ConfigManager destroyed");
        }
    }

    public boolean isInitialized() {
        return initialized.get();
    }

    private void checkInitialized() {
        if (!initialized.get()) {
            init();
        }
    }

    public void setLocalValue(String key, Object value) {
        localCache.put(key, value);
    }

    public Object getLocalValue(String key) {
        return localCache.get(key);
    }

    public void clearLocalCache() {
        localCache.clear();
    }

    public ConfigRollbackManager getRollbackManager() {
        checkInitialized();
        return rollbackManager;
    }

    public ConfigDiffManager getDiffManager() {
        checkInitialized();
        return diffManager;
    }

    public ConfigSnapshot createSnapshot(String description) {
        checkInitialized();
        if (rollbackManager != null) {
            return rollbackManager.createSnapshot("manual", description);
        }
        return null;
    }

    public ConfigRollbackManager.RollbackResult rollbackToSnapshot(String snapshotId) {
        checkInitialized();
        if (rollbackManager != null) {
            return rollbackManager.rollbackToSnapshot(snapshotId);
        }
        return ConfigRollbackManager.RollbackResult.failure("Rollback manager not initialized");
    }

    public ConfigRollbackManager.RollbackResult rollbackToPrevious() {
        checkInitialized();
        if (rollbackManager != null) {
            return rollbackManager.rollbackToPrevious();
        }
        return ConfigRollbackManager.RollbackResult.failure("Rollback manager not initialized");
    }

    public String scheduleRollback(String snapshotId, long delayMs, ConfigRollback rollbackConfig) {
        checkInitialized();
        if (rollbackManager != null) {
            return rollbackManager.scheduleRollback(snapshotId, delayMs, rollbackConfig);
        }
        return null;
    }

    public boolean cancelRollback(String taskId) {
        checkInitialized();
        if (rollbackManager != null) {
            return rollbackManager.cancelRollback(taskId);
        }
        return false;
    }

    public void setRollbackEnabled(boolean enabled) {
        rollbackEnabled.set(enabled);
    }

    public boolean isRollbackEnabled() {
        return rollbackEnabled.get();
    }

    public void setDiffNotificationEnabled(boolean enabled) {
        diffNotificationEnabled.set(enabled);
    }

    public boolean isDiffNotificationEnabled() {
        return diffNotificationEnabled.get();
    }

    @Override
    public void destroy() {
        if (initialized.compareAndSet(true, false)) {
            compositeSource.destroy();
            localCache.clear();
            globalListeners.clear();

            if (rollbackManager != null) {
                rollbackManager.destroy();
            }
            if (diffManager != null) {
                diffManager.destroy();
            }

            logger.info("ConfigManager destroyed");
        }
    }
}

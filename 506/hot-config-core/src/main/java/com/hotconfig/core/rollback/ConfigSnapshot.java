package com.hotconfig.core.rollback;

import com.hotconfig.core.event.ConfigChange;

import java.time.Instant;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public class ConfigSnapshot {

    private final String id;
    private final Instant timestamp;
    private final String sourceName;
    private final Map<String, Object> configValues;
    private final Map<String, ConfigChange> changes;
    private final String description;
    private final SnapshotType type;

    public ConfigSnapshot(String sourceName, Map<String, Object> configValues) {
        this(sourceName, configValues, Collections.emptyMap(), SnapshotType.MANUAL, null);
    }

    public ConfigSnapshot(String sourceName, Map<String, Object> configValues,
                           Map<String, ConfigChange> changes, SnapshotType type, String description) {
        this.id = UUID.randomUUID().toString();
        this.timestamp = Instant.now();
        this.sourceName = sourceName;
        this.configValues = new HashMap<>(configValues);
        this.changes = new HashMap<>(changes);
        this.type = type;
        this.description = description;
    }

    public String getId() {
        return id;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public String getSourceName() {
        return sourceName;
    }

    public Map<String, Object> getConfigValues() {
        return Collections.unmodifiableMap(configValues);
    }

    public Map<String, ConfigChange> getChanges() {
        return Collections.unmodifiableMap(changes);
    }

    public SnapshotType getType() {
        return type;
    }

    public String getDescription() {
        return description;
    }

    public Object getValue(String key) {
        return configValues.get(key);
    }

    public boolean containsKey(String key) {
        return configValues.containsKey(key);
    }

    public int size() {
        return configValues.size();
    }

    @Override
    public String toString() {
        return "ConfigSnapshot{" +
                "id='" + id + '\'' +
                ", timestamp=" + timestamp +
                ", sourceName='" + sourceName + '\'' +
                ", size=" + configValues.size() +
                ", type=" + type +
                '}';
    }

    public enum SnapshotType {
        AUTO_BEFORE_CHANGE,
        AUTO_AFTER_CHANGE,
        AUTO_ROLLBACK,
        MANUAL,
        SYSTEM,
        HEALTH_CHECK
    }
}

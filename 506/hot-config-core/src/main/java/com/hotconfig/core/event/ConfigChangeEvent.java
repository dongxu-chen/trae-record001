package com.hotconfig.core.event;

import java.time.Instant;
import java.util.Map;
import java.util.Set;

public class ConfigChangeEvent {

    private final String sourceName;
    private final Map<String, ConfigChange> changes;
    private final Instant timestamp;
    private final Object source;

    public ConfigChangeEvent(String sourceName, Map<String, ConfigChange> changes, Object source) {
        this.sourceName = sourceName;
        this.changes = changes;
        this.timestamp = Instant.now();
        this.source = source;
    }

    public String getSourceName() {
        return sourceName;
    }

    public Map<String, ConfigChange> getChanges() {
        return changes;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public Object getSource() {
        return source;
    }

    public Set<String> getChangedKeys() {
        return changes.keySet();
    }

    public ConfigChange getChange(String key) {
        return changes.get(key);
    }

    public boolean isKeyChanged(String key) {
        return changes.containsKey(key);
    }

    public boolean isPrefixChanged(String prefix) {
        return changes.keySet().stream().anyMatch(key -> key.startsWith(prefix));
    }
}

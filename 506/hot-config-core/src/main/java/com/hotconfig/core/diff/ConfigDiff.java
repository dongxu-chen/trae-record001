package com.hotconfig.core.diff;

import com.hotconfig.core.event.ConfigChange;

import java.util.*;
import java.util.stream.Collectors;

public class ConfigDiff {

    private final String sourceName;
    private final long timestamp;
    private final Map<String, ConfigChange> changes;
    private final Map<String, Object> beforeValues;
    private final Map<String, Object> afterValues;

    public ConfigDiff(String sourceName, Map<String, ConfigChange> changes,
                       Map<String, Object> beforeValues, Map<String, Object> afterValues) {
        this.sourceName = sourceName;
        this.timestamp = System.currentTimeMillis();
        this.changes = new HashMap<>(changes);
        this.beforeValues = new HashMap<>(beforeValues);
        this.afterValues = new HashMap<>(afterValues);
    }

    public String getSourceName() {
        return sourceName;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public Map<String, ConfigChange> getChanges() {
        return Collections.unmodifiableMap(changes);
    }

    public Map<String, Object> getBeforeValues() {
        return Collections.unmodifiableMap(beforeValues);
    }

    public Map<String, Object> getAfterValues() {
        return Collections.unmodifiableMap(afterValues);
    }

    public Set<String> getChangedKeys() {
        return changes.keySet();
    }

    public int getChangeCount() {
        return changes.size();
    }

    public int getAddedCount() {
        return (int) changes.values().stream()
                .filter(c -> c.getChangeType() == ConfigChange.ChangeType.ADDED)
                .count();
    }

    public int getModifiedCount() {
        return (int) changes.values().stream()
                .filter(c -> c.getChangeType() == ConfigChange.ChangeType.MODIFIED)
                .count();
    }

    public int getDeletedCount() {
        return (int) changes.values().stream()
                .filter(c -> c.getChangeType() == ConfigChange.ChangeType.DELETED)
                .count();
    }

    public ConfigChange getChange(String key) {
        return changes.get(key);
    }

    public boolean hasChange(String key) {
        return changes.containsKey(key);
    }

    public boolean hasChanges() {
        return !changes.isEmpty();
    }

    public Map<String, ConfigChange> getChangesByType(ConfigChange.ChangeType type) {
        return changes.entrySet().stream()
                .filter(e -> e.getValue().getChangeType() == type)
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    public List<String> getSummary() {
        List<String> summary = new ArrayList<>();
        summary.add(String.format("Config changes from '%s': %d total (added: %d, modified: %d, deleted: %d)",
                sourceName, getChangeCount(), getAddedCount(), getModifiedCount(), getDeletedCount()));

        for (Map.Entry<String, ConfigChange> entry : changes.entrySet()) {
            ConfigChange change = entry.getValue();
            String line;
            switch (change.getChangeType()) {
                case ADDED:
                    line = String.format("  [ADDED]   %s = %s", change.getKey(), change.getNewValue());
                    break;
                case MODIFIED:
                    line = String.format("  [MODIFIED] %s: %s -> %s",
                            change.getKey(), change.getOldValue(), change.getNewValue());
                    break;
                case DELETED:
                    line = String.format("  [DELETED]  %s (was: %s)", change.getKey(), change.getOldValue());
                    break;
                default:
                    line = String.format("  [UNKNOWN]  %s", change.getKey());
            }
            summary.add(line);
        }

        return summary;
    }

    public String getSummaryText() {
        return String.join("\n", getSummary());
    }

    public String getFormattedDiff() {
        StringBuilder sb = new StringBuilder();
        sb.append("=== Configuration Change Diff ===\n");
        sb.append(String.format("Source: %s\n", sourceName));
        sb.append(String.format("Timestamp: %tF %tT\n", timestamp, timestamp));
        sb.append(String.format("Total changes: %d\n\n", getChangeCount()));

        for (Map.Entry<String, ConfigChange> entry : changes.entrySet()) {
            ConfigChange change = entry.getValue();
            sb.append(String.format("--- %s ---\n", change.getKey()));
            sb.append(String.format("Type: %s\n", change.getChangeType()));
            sb.append(String.format("Before: %s\n", change.getOldValue()));
            sb.append(String.format("After:  %s\n", change.getNewValue()));
            sb.append("\n");
        }

        return sb.toString();
    }

    public static ConfigDiff fromChanges(String sourceName, Map<String, ConfigChange> changes) {
        Map<String, Object> before = new HashMap<>();
        Map<String, Object> after = new HashMap<>();

        for (Map.Entry<String, ConfigChange> entry : changes.entrySet()) {
            ConfigChange change = entry.getValue();
            before.put(change.getKey(), change.getOldValue());
            after.put(change.getKey(), change.getNewValue());
        }

        return new ConfigDiff(sourceName, changes, before, after);
    }

    public static ConfigDiff compare(String sourceName,
                                     Map<String, Object> before,
                                     Map<String, Object> after) {
        Map<String, ConfigChange> changes = new HashMap<>();
        Set<String> allKeys = new HashSet<>();
        allKeys.addAll(before.keySet());
        allKeys.addAll(after.keySet());

        for (String key : allKeys) {
            Object oldValue = before.get(key);
            Object newValue = after.get(key);

            if (!before.containsKey(key)) {
                changes.put(key, new ConfigChange(key, null, newValue, ConfigChange.ChangeType.ADDED));
            } else if (!after.containsKey(key)) {
                changes.put(key, new ConfigChange(key, oldValue, null, ConfigChange.ChangeType.DELETED));
            } else if (!Objects.equals(oldValue, newValue)) {
                changes.put(key, new ConfigChange(key, oldValue, newValue, ConfigChange.ChangeType.MODIFIED));
            }
        }

        return new ConfigDiff(sourceName, changes, before, after);
    }

    @Override
    public String toString() {
        return "ConfigDiff{" +
                "sourceName='" + sourceName + '\'' +
                ", timestamp=" + timestamp +
                ", changeCount=" + getChangeCount() +
                ", added=" + getAddedCount() +
                ", modified=" + getModifiedCount() +
                ", deleted=" + getDeletedCount() +
                '}';
    }
}

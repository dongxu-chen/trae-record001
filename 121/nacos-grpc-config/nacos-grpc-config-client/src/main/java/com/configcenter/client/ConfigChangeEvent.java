package com.configcenter.client;

import java.util.List;

/**
 * 配置变更事件
 */
public class ConfigChangeEvent {

    private final String dataId;
    private final String group;
    private final List<ChangeItem> changes;
    private final long timestamp;

    public ConfigChangeEvent(String dataId, String group, List<ChangeItem> changes) {
        this.dataId = dataId;
        this.group = group;
        this.changes = changes;
        this.timestamp = System.currentTimeMillis();
    }

    public String getDataId() {
        return dataId;
    }

    public String getGroup() {
        return group;
    }

    public List<ChangeItem> getChanges() {
        return changes;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public boolean hasChanged(String key) {
        return changes.stream().anyMatch(c -> c.getKey().equals(key));
    }

    public ChangeItem getChange(String key) {
        return changes.stream()
                .filter(c -> c.getKey().equals(key))
                .findFirst()
                .orElse(null);
    }

    public int getChangeCount() {
        return changes.size();
    }

    @Override
    public String toString() {
        return "ConfigChangeEvent{" +
                "dataId='" + dataId + '\'' +
                ", group='" + group + '\'' +
                ", changeCount=" + changes.size() +
                ", timestamp=" + timestamp +
                '}';
    }

    /**
     * 变更项
     */
    public static class ChangeItem {
        private final String key;
        private final String oldValue;
        private final String newValue;
        private final ChangeType changeType;

        public ChangeItem(String key, String oldValue, String newValue, ChangeType changeType) {
            this.key = key;
            this.oldValue = oldValue;
            this.newValue = newValue;
            this.changeType = changeType;
        }

        public String getKey() {
            return key;
        }

        public String getOldValue() {
            return oldValue;
        }

        public String getNewValue() {
            return newValue;
        }

        public ChangeType getChangeType() {
            return changeType;
        }

        @Override
        public String toString() {
            return "ChangeItem{" +
                    "key='" + key + '\'' +
                    ", oldValue='" + oldValue + '\'' +
                    ", newValue='" + newValue + '\'' +
                    ", changeType=" + changeType +
                    '}';
        }
    }

    /**
     * 变更类型
     */
    public enum ChangeType {
        ADDED,
        MODIFIED,
        DELETED
    }
}

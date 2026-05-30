package com.hotconfig.core.event;

public class ConfigChange {

    private final String key;
    private final Object oldValue;
    private final Object newValue;
    private final ChangeType changeType;

    public ConfigChange(String key, Object oldValue, Object newValue, ChangeType changeType) {
        this.key = key;
        this.oldValue = oldValue;
        this.newValue = newValue;
        this.changeType = changeType;
    }

    public String getKey() {
        return key;
    }

    public Object getOldValue() {
        return oldValue;
    }

    public Object getNewValue() {
        return newValue;
    }

    public ChangeType getChangeType() {
        return changeType;
    }

    public enum ChangeType {
        ADDED,
        MODIFIED,
        DELETED
    }
}

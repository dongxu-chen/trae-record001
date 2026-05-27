package com.api.docs.version;

public class FieldChangeDetail {
    private String fieldName;
    private ChangeType changeType;
    private String oldValue;
    private String newValue;
    private String oldType;
    private String newType;
    private Boolean oldRequired;
    private Boolean newRequired;
    private String description;

    public enum ChangeType {
        ADDED, REMOVED, TYPE_CHANGED, REQUIRED_CHANGED, DESCRIPTION_CHANGED, OTHER
    }

    public String getFieldName() {
        return fieldName;
    }

    public void setFieldName(String fieldName) {
        this.fieldName = fieldName;
    }

    public ChangeType getChangeType() {
        return changeType;
    }

    public void setChangeType(ChangeType changeType) {
        this.changeType = changeType;
    }

    public String getOldValue() {
        return oldValue;
    }

    public void setOldValue(String oldValue) {
        this.oldValue = oldValue;
    }

    public String getNewValue() {
        return newValue;
    }

    public void setNewValue(String newValue) {
        this.newValue = newValue;
    }

    public String getOldType() {
        return oldType;
    }

    public void setOldType(String oldType) {
        this.oldType = oldType;
    }

    public String getNewType() {
        return newType;
    }

    public void setNewType(String newType) {
        this.newType = newType;
    }

    public Boolean getOldRequired() {
        return oldRequired;
    }

    public void setOldRequired(Boolean oldRequired) {
        this.oldRequired = oldRequired;
    }

    public Boolean getNewRequired() {
        return newRequired;
    }

    public void setNewRequired(Boolean newRequired) {
        this.newRequired = newRequired;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }
}
package com.api.docs.version;

public class ParameterChangeDetail {
    private String parameterName;
    private ChangeType changeType;
    private String oldIn;
    private String newIn;
    private String oldType;
    private String newType;
    private Boolean oldRequired;
    private Boolean newRequired;

    public enum ChangeType {
        ADDED, REMOVED, TYPE_CHANGED, REQUIRED_CHANGED, POSITION_CHANGED, OTHER
    }

    public String getParameterName() {
        return parameterName;
    }

    public void setParameterName(String parameterName) {
        this.parameterName = parameterName;
    }

    public ChangeType getChangeType() {
        return changeType;
    }

    public void setChangeType(ChangeType changeType) {
        this.changeType = changeType;
    }

    public String getOldIn() {
        return oldIn;
    }

    public void setOldIn(String oldIn) {
        this.oldIn = oldIn;
    }

    public String getNewIn() {
        return newIn;
    }

    public void setNewIn(String newIn) {
        this.newIn = newIn;
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
}
package com.api.docs.version;

import java.util.ArrayList;
import java.util.List;

public class OperationChangeDetail {
    private String operationPath;
    private String httpMethod;
    private ChangeType changeType;
    private String oldSummary;
    private String newSummary;
    private Boolean oldDeprecated;
    private Boolean newDeprecated;
    private List<ParameterChangeDetail> parameterChanges = new ArrayList<>();
    private String oldRequestBodyType;
    private String newRequestBodyType;
    private String oldResponseType;
    private String newResponseType;

    public enum ChangeType {
        ADDED, REMOVED, MODIFIED
    }

    public String getOperationPath() {
        return operationPath;
    }

    public void setOperationPath(String operationPath) {
        this.operationPath = operationPath;
    }

    public String getHttpMethod() {
        return httpMethod;
    }

    public void setHttpMethod(String httpMethod) {
        this.httpMethod = httpMethod;
    }

    public ChangeType getChangeType() {
        return changeType;
    }

    public void setChangeType(ChangeType changeType) {
        this.changeType = changeType;
    }

    public String getOldSummary() {
        return oldSummary;
    }

    public void setOldSummary(String oldSummary) {
        this.oldSummary = oldSummary;
    }

    public String getNewSummary() {
        return newSummary;
    }

    public void setNewSummary(String newSummary) {
        this.newSummary = newSummary;
    }

    public Boolean getOldDeprecated() {
        return oldDeprecated;
    }

    public void setOldDeprecated(Boolean oldDeprecated) {
        this.oldDeprecated = oldDeprecated;
    }

    public Boolean getNewDeprecated() {
        return newDeprecated;
    }

    public void setNewDeprecated(Boolean newDeprecated) {
        this.newDeprecated = newDeprecated;
    }

    public List<ParameterChangeDetail> getParameterChanges() {
        return parameterChanges;
    }

    public void setParameterChanges(List<ParameterChangeDetail> parameterChanges) {
        this.parameterChanges = parameterChanges;
    }

    public void addParameterChange(ParameterChangeDetail change) {
        this.parameterChanges.add(change);
    }

    public String getOldRequestBodyType() {
        return oldRequestBodyType;
    }

    public void setOldRequestBodyType(String oldRequestBodyType) {
        this.oldRequestBodyType = oldRequestBodyType;
    }

    public String getNewRequestBodyType() {
        return newRequestBodyType;
    }

    public void setNewRequestBodyType(String newRequestBodyType) {
        this.newRequestBodyType = newRequestBodyType;
    }

    public String getOldResponseType() {
        return oldResponseType;
    }

    public void setOldResponseType(String oldResponseType) {
        this.oldResponseType = oldResponseType;
    }

    public String getNewResponseType() {
        return newResponseType;
    }

    public void setNewResponseType(String newResponseType) {
        this.newResponseType = newResponseType;
    }
}
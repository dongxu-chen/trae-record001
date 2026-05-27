package com.api.docs.version;

import java.util.ArrayList;
import java.util.List;

public class VersionDiff {
    private String oldVersion;
    private String newVersion;

    private List<String> addedPaths = new ArrayList<>();
    private List<String> removedPaths = new ArrayList<>();
    private List<OperationChangeDetail> operationChanges = new ArrayList<>();
    private List<String> addedSchemas = new ArrayList<>();
    private List<String> removedSchemas = new ArrayList<>();
    private List<String> modifiedSchemas = new ArrayList<>();
    private List<FieldChangeDetail> fieldChanges = new ArrayList<>();

    public String getOldVersion() {
        return oldVersion;
    }

    public void setOldVersion(String oldVersion) {
        this.oldVersion = oldVersion;
    }

    public String getNewVersion() {
        return newVersion;
    }

    public void setNewVersion(String newVersion) {
        this.newVersion = newVersion;
    }

    public List<String> getAddedPaths() {
        return addedPaths;
    }

    public void setAddedPaths(List<String> addedPaths) {
        this.addedPaths = addedPaths;
    }

    public void addAddedPath(String path) {
        this.addedPaths.add(path);
    }

    public List<String> getRemovedPaths() {
        return removedPaths;
    }

    public void setRemovedPaths(List<String> removedPaths) {
        this.removedPaths = removedPaths;
    }

    public void addRemovedPath(String path) {
        this.removedPaths.add(path);
    }

    public List<OperationChangeDetail> getOperationChanges() {
        return operationChanges;
    }

    public void setOperationChanges(List<OperationChangeDetail> operationChanges) {
        this.operationChanges = operationChanges;
    }

    public void addOperationChange(OperationChangeDetail change) {
        this.operationChanges.add(change);
    }

    public List<String> getAddedOperations() {
        List<String> result = new ArrayList<>();
        for (OperationChangeDetail change : operationChanges) {
            if (change.getChangeType() == OperationChangeDetail.ChangeType.ADDED) {
                result.add(change.getHttpMethod() + " " + change.getOperationPath());
            }
        }
        return result;
    }

    public List<String> getRemovedOperations() {
        List<String> result = new ArrayList<>();
        for (OperationChangeDetail change : operationChanges) {
            if (change.getChangeType() == OperationChangeDetail.ChangeType.REMOVED) {
                result.add(change.getHttpMethod() + " " + change.getOperationPath());
            }
        }
        return result;
    }

    public List<String> getModifiedOperations() {
        List<String> result = new ArrayList<>();
        for (OperationChangeDetail change : operationChanges) {
            if (change.getChangeType() == OperationChangeDetail.ChangeType.MODIFIED) {
                result.add(change.getHttpMethod() + " " + change.getOperationPath());
            }
        }
        return result;
    }

    public List<String> getAddedSchemas() {
        return addedSchemas;
    }

    public void setAddedSchemas(List<String> addedSchemas) {
        this.addedSchemas = addedSchemas;
    }

    public void addAddedSchema(String schema) {
        this.addedSchemas.add(schema);
    }

    public List<String> getRemovedSchemas() {
        return removedSchemas;
    }

    public void setRemovedSchemas(List<String> removedSchemas) {
        this.removedSchemas = removedSchemas;
    }

    public void addRemovedSchema(String schema) {
        this.removedSchemas.add(schema);
    }

    public List<String> getModifiedSchemas() {
        return modifiedSchemas;
    }

    public void setModifiedSchemas(List<String> modifiedSchemas) {
        this.modifiedSchemas = modifiedSchemas;
    }

    public void addModifiedSchema(String schema) {
        this.modifiedSchemas.add(schema);
    }

    public List<FieldChangeDetail> getFieldChanges() {
        return fieldChanges;
    }

    public void setFieldChanges(List<FieldChangeDetail> fieldChanges) {
        this.fieldChanges = fieldChanges;
    }

    public void addFieldChange(FieldChangeDetail change) {
        this.fieldChanges.add(change);
    }

    public List<String> getAddedFields() {
        List<String> result = new ArrayList<>();
        for (FieldChangeDetail change : fieldChanges) {
            if (change.getChangeType() == FieldChangeDetail.ChangeType.ADDED) {
                result.add(change.getFieldName());
            }
        }
        return result;
    }

    public List<String> getRemovedFields() {
        List<String> result = new ArrayList<>();
        for (FieldChangeDetail change : fieldChanges) {
            if (change.getChangeType() == FieldChangeDetail.ChangeType.REMOVED) {
                result.add(change.getFieldName());
            }
        }
        return result;
    }

    public List<String> getModifiedFields() {
        List<String> result = new ArrayList<>();
        for (FieldChangeDetail change : fieldChanges) {
            if (change.getChangeType() != FieldChangeDetail.ChangeType.ADDED &&
                change.getChangeType() != FieldChangeDetail.ChangeType.REMOVED) {
                result.add(change.getFieldName());
            }
        }
        return result;
    }
}
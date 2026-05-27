package com.api.docs.model;

import java.util.ArrayList;
import java.util.List;

public class ModelInfo {
    private String className;
    private String packageName;
    private String description;
    private List<FieldInfo> fields = new ArrayList<>();

    public String getClassName() {
        return className;
    }

    public void setClassName(String className) {
        this.className = className;
    }

    public String getPackageName() {
        return packageName;
    }

    public void setPackageName(String packageName) {
        this.packageName = packageName;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public List<FieldInfo> getFields() {
        return fields;
    }

    public void setFields(List<FieldInfo> fields) {
        this.fields = fields;
    }

    public void addField(FieldInfo field) {
        this.fields.add(field);
    }
}
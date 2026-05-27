package com.api.docs.model;

public class ParameterInfo {
    private String name;
    private String type;
    private String description;
    private String in;
    private boolean required;
    private String defaultValue;
    private String example;
    private String[] allowableValues;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getIn() {
        return in;
    }

    public void setIn(String in) {
        this.in = in;
    }

    public boolean isRequired() {
        return required;
    }

    public void setRequired(boolean required) {
        this.required = required;
    }

    public String getDefaultValue() {
        return defaultValue;
    }

    public void setDefaultValue(String defaultValue) {
        this.defaultValue = defaultValue;
    }

    public String getExample() {
        return example;
    }

    public void setExample(String example) {
        this.example = example;
    }

    public String[] getAllowableValues() {
        return allowableValues;
    }

    public void setAllowableValues(String[] allowableValues) {
        this.allowableValues = allowableValues;
    }
}
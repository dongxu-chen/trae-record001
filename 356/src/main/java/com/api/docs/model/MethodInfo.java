package com.api.docs.model;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MethodInfo {
    private String name;
    private String httpMethod;
    private String path;
    private String summary;
    private String description;
    private String businessType;
    private String owner;
    private String createTime;
    private String updateTime;
    private String deprecatedReason;
    private List<ParameterInfo> parameters = new ArrayList<>();
    private String requestBodyType;
    private Object requestBodyExample;
    private String responseType;
    private Object responseExample;
    private List<String> tags = new ArrayList<>();
    private boolean deprecated;
    private boolean enableMock;
    private Map<String, String> extensions = new HashMap<>();

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getHttpMethod() {
        return httpMethod;
    }

    public void setHttpMethod(String httpMethod) {
        this.httpMethod = httpMethod;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getBusinessType() {
        return businessType;
    }

    public void setBusinessType(String businessType) {
        this.businessType = businessType;
    }

    public String getOwner() {
        return owner;
    }

    public void setOwner(String owner) {
        this.owner = owner;
    }

    public String getCreateTime() {
        return createTime;
    }

    public void setCreateTime(String createTime) {
        this.createTime = createTime;
    }

    public String getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(String updateTime) {
        this.updateTime = updateTime;
    }

    public String getDeprecatedReason() {
        return deprecatedReason;
    }

    public void setDeprecatedReason(String deprecatedReason) {
        this.deprecatedReason = deprecatedReason;
    }

    public List<ParameterInfo> getParameters() {
        return parameters;
    }

    public void setParameters(List<ParameterInfo> parameters) {
        this.parameters = parameters;
    }

    public void addParameter(ParameterInfo parameter) {
        this.parameters.add(parameter);
    }

    public String getRequestBodyType() {
        return requestBodyType;
    }

    public void setRequestBodyType(String requestBodyType) {
        this.requestBodyType = requestBodyType;
    }

    public Object getRequestBodyExample() {
        return requestBodyExample;
    }

    public void setRequestBodyExample(Object requestBodyExample) {
        this.requestBodyExample = requestBodyExample;
    }

    public String getResponseType() {
        return responseType;
    }

    public void setResponseType(String responseType) {
        this.responseType = responseType;
    }

    public Object getResponseExample() {
        return responseExample;
    }

    public void setResponseExample(Object responseExample) {
        this.responseExample = responseExample;
    }

    public List<String> getTags() {
        return tags;
    }

    public void setTags(List<String> tags) {
        this.tags = tags;
    }

    public void addTag(String tag) {
        this.tags.add(tag);
    }

    public boolean isDeprecated() {
        return deprecated;
    }

    public void setDeprecated(boolean deprecated) {
        this.deprecated = deprecated;
    }

    public boolean isEnableMock() {
        return enableMock;
    }

    public void setEnableMock(boolean enableMock) {
        this.enableMock = enableMock;
    }

    public Map<String, String> getExtensions() {
        return extensions;
    }

    public void setExtensions(Map<String, String> extensions) {
        this.extensions = extensions;
    }

    public void addExtension(String key, String value) {
        this.extensions.put(key, value);
    }
}
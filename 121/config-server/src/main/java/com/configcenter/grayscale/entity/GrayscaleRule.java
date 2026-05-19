package com.configcenter.grayscale.entity;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

public class GrayscaleRule {

    private String id;
    private String serviceName;
    private String profile;
    private String label;
    private RuleType type;
    private List<String> targetIps = new ArrayList<>();
    private List<String> targetInstances = new ArrayList<>();
    private Integer percentage;
    private GrayscaleStatus status;
    private String createdBy;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String configVersion;
    private String description;

    public enum RuleType {
        IP,
        INSTANCE,
        PERCENTAGE
    }

    public enum GrayscaleStatus {
        DRAFT,
        ACTIVE,
        PAUSED,
        COMPLETED,
        CANCELLED
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getServiceName() {
        return serviceName;
    }

    public void setServiceName(String serviceName) {
        this.serviceName = serviceName;
    }

    public String getProfile() {
        return profile;
    }

    public void setProfile(String profile) {
        this.profile = profile;
    }

    public String getLabel() {
        return label;
    }

    public void setLabel(String label) {
        this.label = label;
    }

    public RuleType getType() {
        return type;
    }

    public void setType(RuleType type) {
        this.type = type;
    }

    public List<String> getTargetIps() {
        return targetIps;
    }

    public void setTargetIps(List<String> targetIps) {
        this.targetIps = targetIps;
    }

    public List<String> getTargetInstances() {
        return targetInstances;
    }

    public void setTargetInstances(List<String> targetInstances) {
        this.targetInstances = targetInstances;
    }

    public Integer getPercentage() {
        return percentage;
    }

    public void setPercentage(Integer percentage) {
        this.percentage = percentage;
    }

    public GrayscaleStatus getStatus() {
        return status;
    }

    public void setStatus(GrayscaleStatus status) {
        this.status = status;
    }

    public String getCreatedBy() {
        return createdBy;
    }

    public void setCreatedBy(String createdBy) {
        this.createdBy = createdBy;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public String getConfigVersion() {
        return configVersion;
    }

    public void setConfigVersion(String configVersion) {
        this.configVersion = configVersion;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }
}

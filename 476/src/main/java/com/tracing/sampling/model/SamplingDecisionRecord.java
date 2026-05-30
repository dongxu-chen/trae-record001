package com.tracing.sampling.model;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class SamplingDecisionRecord {
    private long timestamp;
    private String traceId;
    private String spanName;
    private String reason;
    private double baseRate;
    private double finalRate;
    private long predictedLatency;
    private String serviceName;
    private String serviceImportance;
    private boolean parentSampled;
    private boolean isError;
    private long actualLatency;
    private long httpStatus;
    private String endpointKey;
    
    private double importanceMultiplier;
    private double endpointMultiplier;
    private double errorRateMultiplier;
    private double adaptiveMultiplier;
    
    private List<SamplingDecisionTree.DecisionStep> decisionSteps;
    private Map<String, Object> decisionFactors;

    public SamplingDecisionRecord() {
        this.decisionSteps = new ArrayList<>();
    }

    public SamplingDecisionRecord(long timestamp, String reason, double baseRate, 
                                  double finalRate, long predictedLatency, String serviceName) {
        this.timestamp = timestamp;
        this.reason = reason;
        this.baseRate = baseRate;
        this.finalRate = finalRate;
        this.predictedLatency = predictedLatency;
        this.serviceName = serviceName;
        this.decisionSteps = new ArrayList<>();
    }

    public long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getSpanName() {
        return spanName;
    }

    public void setSpanName(String spanName) {
        this.spanName = spanName;
    }

    public String getReason() {
        return reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    public double getBaseRate() {
        return baseRate;
    }

    public void setBaseRate(double baseRate) {
        this.baseRate = baseRate;
    }

    public double getFinalRate() {
        return finalRate;
    }

    public void setFinalRate(double finalRate) {
        this.finalRate = finalRate;
    }

    public long getPredictedLatency() {
        return predictedLatency;
    }

    public void setPredictedLatency(long predictedLatency) {
        this.predictedLatency = predictedLatency;
    }

    public String getServiceName() {
        return serviceName;
    }

    public void setServiceName(String serviceName) {
        this.serviceName = serviceName;
    }

    public String getServiceImportance() {
        return serviceImportance;
    }

    public void setServiceImportance(String serviceImportance) {
        this.serviceImportance = serviceImportance;
    }

    public boolean isParentSampled() {
        return parentSampled;
    }

    public void setParentSampled(boolean parentSampled) {
        this.parentSampled = parentSampled;
    }

    public boolean isError() {
        return isError;
    }

    public void setError(boolean error) {
        isError = error;
    }

    public long getActualLatency() {
        return actualLatency;
    }

    public void setActualLatency(long actualLatency) {
        this.actualLatency = actualLatency;
    }

    public long getHttpStatus() {
        return httpStatus;
    }

    public void setHttpStatus(long httpStatus) {
        this.httpStatus = httpStatus;
    }

    public String getEndpointKey() {
        return endpointKey;
    }

    public void setEndpointKey(String endpointKey) {
        this.endpointKey = endpointKey;
    }

    public double getImportanceMultiplier() {
        return importanceMultiplier;
    }

    public void setImportanceMultiplier(double importanceMultiplier) {
        this.importanceMultiplier = importanceMultiplier;
    }

    public double getEndpointMultiplier() {
        return endpointMultiplier;
    }

    public void setEndpointMultiplier(double endpointMultiplier) {
        this.endpointMultiplier = endpointMultiplier;
    }

    public double getErrorRateMultiplier() {
        return errorRateMultiplier;
    }

    public void setErrorRateMultiplier(double errorRateMultiplier) {
        this.errorRateMultiplier = errorRateMultiplier;
    }

    public double getAdaptiveMultiplier() {
        return adaptiveMultiplier;
    }

    public void setAdaptiveMultiplier(double adaptiveMultiplier) {
        this.adaptiveMultiplier = adaptiveMultiplier;
    }

    public List<SamplingDecisionTree.DecisionStep> getDecisionSteps() {
        return decisionSteps;
    }

    public void setDecisionSteps(List<SamplingDecisionTree.DecisionStep> decisionSteps) {
        this.decisionSteps = decisionSteps;
    }

    public Map<String, Object> getDecisionFactors() {
        return decisionFactors;
    }

    public void setDecisionFactors(Map<String, Object> decisionFactors) {
        this.decisionFactors = decisionFactors;
    }
}

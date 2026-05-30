package com.tracing.sampling.model;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class TraceSamplingContext implements Serializable {

    private static final long serialVersionUID = 1L;

    private String traceId;
    private Boolean rootSampled;
    private String rootDecisionReason;
    private long rootDecisionTime;
    private String initiatingService;
    private Map<String, ServiceTraceInfo> serviceInfoMap;
    private int totalSpans;
    private int sampledSpans;
    private boolean consistentSamplingEnabled;

    public TraceSamplingContext() {
        this.serviceInfoMap = new ConcurrentHashMap<>();
        this.consistentSamplingEnabled = true;
    }

    public TraceSamplingContext(String traceId) {
        this();
        this.traceId = traceId;
        this.rootDecisionTime = System.currentTimeMillis();
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public Boolean getRootSampled() {
        return rootSampled;
    }

    public void setRootSampled(Boolean rootSampled) {
        this.rootSampled = rootSampled;
    }

    public String getRootDecisionReason() {
        return rootDecisionReason;
    }

    public void setRootDecisionReason(String rootDecisionReason) {
        this.rootDecisionReason = rootDecisionReason;
    }

    public long getRootDecisionTime() {
        return rootDecisionTime;
    }

    public void setRootDecisionTime(long rootDecisionTime) {
        this.rootDecisionTime = rootDecisionTime;
    }

    public String getInitiatingService() {
        return initiatingService;
    }

    public void setInitiatingService(String initiatingService) {
        this.initiatingService = initiatingService;
    }

    public Map<String, ServiceTraceInfo> getServiceInfoMap() {
        return serviceInfoMap;
    }

    public void setServiceInfoMap(Map<String, ServiceTraceInfo> serviceInfoMap) {
        this.serviceInfoMap = serviceInfoMap;
    }

    public void addServiceInfo(String serviceName, ServiceTraceInfo info) {
        this.serviceInfoMap.put(serviceName, info);
        this.totalSpans += info.getSpanCount();
        if (Boolean.TRUE.equals(rootSampled)) {
            this.sampledSpans += info.getSpanCount();
        }
    }

    public int getTotalSpans() {
        return totalSpans;
    }

    public void setTotalSpans(int totalSpans) {
        this.totalSpans = totalSpans;
    }

    public int getSampledSpans() {
        return sampledSpans;
    }

    public void setSampledSpans(int sampledSpans) {
        this.sampledSpans = sampledSpans;
    }

    public boolean isConsistentSamplingEnabled() {
        return consistentSamplingEnabled;
    }

    public void setConsistentSamplingEnabled(boolean consistentSamplingEnabled) {
        this.consistentSamplingEnabled = consistentSamplingEnabled;
    }

    public boolean hasRootDecision() {
        return rootSampled != null;
    }

    public static class ServiceTraceInfo implements Serializable {
        private static final long serialVersionUID = 1L;
        
        private String serviceName;
        private int spanCount;
        private int errorCount;
        private long totalLatency;
        private long firstSeenTime;
        private long lastSeenTime;
        private Map<String, Object> metadata;

        public ServiceTraceInfo() {
            this.metadata = new HashMap<>();
            this.firstSeenTime = System.currentTimeMillis();
            this.lastSeenTime = System.currentTimeMillis();
        }

        public ServiceTraceInfo(String serviceName) {
            this();
            this.serviceName = serviceName;
        }

        public String getServiceName() {
            return serviceName;
        }

        public void setServiceName(String serviceName) {
            this.serviceName = serviceName;
        }

        public int getSpanCount() {
            return spanCount;
        }

        public void setSpanCount(int spanCount) {
            this.spanCount = spanCount;
        }

        public void incrementSpanCount() {
            this.spanCount++;
            this.lastSeenTime = System.currentTimeMillis();
        }

        public int getErrorCount() {
            return errorCount;
        }

        public void setErrorCount(int errorCount) {
            this.errorCount = errorCount;
        }

        public void incrementErrorCount() {
            this.errorCount++;
        }

        public long getTotalLatency() {
            return totalLatency;
        }

        public void setTotalLatency(long totalLatency) {
            this.totalLatency = totalLatency;
        }

        public void addLatency(long latency) {
            this.totalLatency += latency;
        }

        public long getFirstSeenTime() {
            return firstSeenTime;
        }

        public void setFirstSeenTime(long firstSeenTime) {
            this.firstSeenTime = firstSeenTime;
        }

        public long getLastSeenTime() {
            return lastSeenTime;
        }

        public void setLastSeenTime(long lastSeenTime) {
            this.lastSeenTime = lastSeenTime;
        }

        public Map<String, Object> getMetadata() {
            return metadata;
        }

        public void setMetadata(Map<String, Object> metadata) {
            this.metadata = metadata;
        }

        public void addMetadata(String key, Object value) {
            this.metadata.put(key, value);
        }

        public double getAverageLatency() {
            return spanCount > 0 ? (double) totalLatency / spanCount : 0;
        }

        public double getErrorRate() {
            return spanCount > 0 ? (double) errorCount / spanCount : 0;
        }
    }
}

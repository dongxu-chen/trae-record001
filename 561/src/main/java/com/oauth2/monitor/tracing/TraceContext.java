package com.oauth2.monitor.tracing;

import org.springframework.context.annotation.Scope;
import org.springframework.context.annotation.ScopedProxyMode;
import org.springframework.stereotype.Component;
import org.springframework.web.context.WebApplicationContext;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Component
@Scope(value = WebApplicationContext.SCOPE_REQUEST, proxyMode = ScopedProxyMode.TARGET_CLASS)
public class TraceContext implements Serializable {

    private static final long serialVersionUID = 1L;

    private String traceId;
    private String requestId;
    private String flowId;
    private String clientId;
    private String userId;
    private String parentSpanId;
    private String spanId;
    private final Map<String, String> attributes = new HashMap<>();
    private long startTime;

    public TraceContext() {
        this.traceId = generateId();
        this.requestId = generateId();
        this.spanId = generateId();
        this.startTime = System.currentTimeMillis();
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId != null ? traceId : generateId();
    }

    public String getRequestId() {
        return requestId;
    }

    public void setRequestId(String requestId) {
        this.requestId = requestId;
    }

    public String getFlowId() {
        return flowId;
    }

    public void setFlowId(String flowId) {
        this.flowId = flowId;
    }

    public String getClientId() {
        return clientId;
    }

    public void setClientId(String clientId) {
        this.clientId = clientId;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getParentSpanId() {
        return parentSpanId;
    }

    public void setParentSpanId(String parentSpanId) {
        this.parentSpanId = parentSpanId;
    }

    public String getSpanId() {
        return spanId;
    }

    public void setSpanId(String spanId) {
        this.spanId = spanId;
    }

    public long getStartTime() {
        return startTime;
    }

    public void setStartTime(long startTime) {
        this.startTime = startTime;
    }

    public void putAttribute(String key, String value) {
        attributes.put(key, value);
    }

    public String getAttribute(String key) {
        return attributes.get(key);
    }

    public Map<String, String> getAttributes() {
        return new HashMap<>(attributes);
    }

    public long getDurationMs() {
        return System.currentTimeMillis() - startTime;
    }

    public TraceContext createChildSpan() {
        TraceContext child = new TraceContext();
        child.traceId = this.traceId;
        child.parentSpanId = this.spanId;
        child.flowId = this.flowId;
        child.clientId = this.clientId;
        child.userId = this.userId;
        child.attributes.putAll(this.attributes);
        return child;
    }

    private String generateId() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    public Map<String, String> toMdcContext() {
        Map<String, String> mdc = new HashMap<>();
        mdc.put("traceId", traceId);
        mdc.put("requestId", requestId);
        if (flowId != null) mdc.put("flowId", flowId);
        if (clientId != null) mdc.put("clientId", clientId);
        if (userId != null) mdc.put("userId", userId);
        if (spanId != null) mdc.put("spanId", spanId);
        if (parentSpanId != null) mdc.put("parentSpanId", parentSpanId);
        return mdc;
    }

    @Override
    public String toString() {
        return String.format(
                "TraceContext{traceId='%s', spanId='%s', flowId='%s', clientId='%s', userId='%s', duration=%dms}",
                traceId, spanId, flowId, clientId, userId, getDurationMs()
        );
    }
}

package com.oauth2.monitor.tracing;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class AuthorizationFlowTraceService {

    private final Map<String, AuthorizationFlowTrace> activeFlows = new ConcurrentHashMap<>();
    private final List<AuthorizationFlowTrace> completedFlows = new ArrayList<>();
    private static final int MAX_COMPLETED_FLOWS = 10000;

    public AuthorizationFlowTrace startFlow(String traceId, String flowId, String clientId,
                                            String ipAddress, String userAgent) {
        AuthorizationFlowTrace flow = AuthorizationFlowTrace.builder()
                .traceId(traceId)
                .flowId(flowId)
                .clientId(clientId)
                .status(AuthorizationFlowTrace.FlowStatus.STARTED.name())
                .startTime(Instant.now())
                .ipAddress(ipAddress)
                .userAgent(userAgent)
                .build();

        activeFlows.put(flowId, flow);
        log.info("Authorization flow started - traceId: {}, flowId: {}, clientId: {}",
                traceId, flowId, clientId);

        return flow;
    }

    public void recordStep(String flowId, AuthorizationFlowTrace.FlowStep step, Map<String, String> attributes) {
        AuthorizationFlowTrace flow = activeFlows.get(flowId);
        if (flow != null) {
            if (attributes != null) {
                flow.getCustomAttributes().putAll(attributes);
            }
            log.debug("Flow step recorded - flowId: {}, step: {}", flowId, step.getValue());
        }
    }

    public void authorizationCodeIssued(String flowId, String userId) {
        AuthorizationFlowTrace flow = activeFlows.get(flowId);
        if (flow != null) {
            flow.setStatus(AuthorizationFlowTrace.FlowStatus.AUTHORIZATION_CODE_ISSUED.name());
            flow.setUserId(userId);
            TraceIdFilter.setUserId(userId);
            log.info("Authorization code issued - flowId: {}, userId: {}", flowId, userId);
        }
    }

    public void tokenExchanged(String flowId, String grantType) {
        AuthorizationFlowTrace flow = activeFlows.get(flowId);
        if (flow != null) {
            flow.setStatus(AuthorizationFlowTrace.FlowStatus.TOKEN_EXCHANGED.name());
            flow.setGrantType(grantType);
            log.info("Token exchanged - flowId: {}, grantType: {}", flowId, grantType);
        }
    }

    public void completeFlow(String flowId) {
        AuthorizationFlowTrace flow = activeFlows.remove(flowId);
        if (flow != null) {
            flow.setStatus(AuthorizationFlowTrace.FlowStatus.COMPLETED.name());
            flow.setEndTime(Instant.now());
            flow.setDurationMs(Duration.between(flow.getStartTime(), flow.getEndTime()).toMillis());
            addCompletedFlow(flow);
            log.info("Authorization flow completed - flowId: {}, duration: {}ms",
                    flowId, flow.getDurationMs());
        }
    }

    public void failFlow(String flowId, String errorCode, String errorDescription) {
        AuthorizationFlowTrace flow = activeFlows.remove(flowId);
        if (flow != null) {
            flow.setStatus(AuthorizationFlowTrace.FlowStatus.FAILED.name());
            flow.setErrorCode(errorCode);
            flow.setErrorDescription(errorDescription);
            flow.setEndTime(Instant.now());
            flow.setDurationMs(Duration.between(flow.getStartTime(), flow.getEndTime()).toMillis());
            addCompletedFlow(flow);
            log.warn("Authorization flow failed - flowId: {}, errorCode: {}, description: {}",
                    flowId, errorCode, errorDescription);
        }
    }

    private void addCompletedFlow(AuthorizationFlowTrace flow) {
        synchronized (completedFlows) {
            if (completedFlows.size() >= MAX_COMPLETED_FLOWS) {
                completedFlows.remove(0);
            }
            completedFlows.add(flow);
        }
    }

    public AuthorizationFlowTrace getFlow(String flowId) {
        AuthorizationFlowTrace flow = activeFlows.get(flowId);
        if (flow == null) {
            synchronized (completedFlows) {
                flow = completedFlows.stream()
                        .filter(f -> flowId.equals(f.getFlowId()))
                        .findFirst()
                        .orElse(null);
            }
        }
        return flow;
    }

    public List<AuthorizationFlowTrace> getFlowsByTraceId(String traceId) {
        List<AuthorizationFlowTrace> result = new ArrayList<>();

        activeFlows.values().stream()
                .filter(f -> traceId.equals(f.getTraceId()))
                .forEach(result::add);

        synchronized (completedFlows) {
            completedFlows.stream()
                    .filter(f -> traceId.equals(f.getTraceId()))
                    .forEach(result::add);
        }

        return result;
    }

    public List<AuthorizationFlowTrace> getActiveFlows() {
        return new ArrayList<>(activeFlows.values());
    }

    public List<AuthorizationFlowTrace> getFailedFlows(int limit) {
        List<AuthorizationFlowTrace> result = new ArrayList<>();
        synchronized (completedFlows) {
            completedFlows.stream()
                    .filter(f -> AuthorizationFlowTrace.FlowStatus.FAILED.name().equals(f.getStatus()))
                    .skip(Math.max(0, completedFlows.size() - limit))
                    .forEach(result::add);
        }
        return result;
    }

    public long getActiveFlowCount() {
        return activeFlows.size();
    }
}

package com.oauth2.monitor;

import com.oauth2.monitor.tracing.AuthorizationFlowTrace;
import com.oauth2.monitor.tracing.AuthorizationFlowTraceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@DisplayName("Authorization Flow Trace Service Tests")
class AuthorizationFlowTraceServiceTest {

    private AuthorizationFlowTraceService traceService;

    @BeforeEach
    void setUp() {
        traceService = new AuthorizationFlowTraceService();
    }

    @Test
    @DisplayName("Test starting a new authorization flow")
    void testStartFlow() {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        String flowId = "flow-12345";
        String clientId = "client-test";
        String ipAddress = "192.168.1.1";
        String userAgent = "Mozilla/5.0 Test";

        AuthorizationFlowTrace flow = traceService.startFlow(traceId, flowId, clientId, ipAddress, userAgent);

        assertNotNull(flow);
        assertEquals(traceId, flow.getTraceId());
        assertEquals(flowId, flow.getFlowId());
        assertEquals(clientId, flow.getClientId());
        assertEquals(ipAddress, flow.getIpAddress());
        assertEquals(userAgent, flow.getUserAgent());
        assertEquals(AuthorizationFlowTrace.FlowStatus.STARTED.name(), flow.getStatus());
        assertNotNull(flow.getStartTime());
    }

    @Test
    @DisplayName("Test authorization code issued step")
    void testAuthorizationCodeIssued() {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        String flowId = "flow-code-issued";

        traceService.startFlow(traceId, flowId, "client1", "192.168.1.1", "TestAgent");
        traceService.authorizationCodeIssued(flowId, "user-john");

        AuthorizationFlowTrace flow = traceService.getFlow(flowId);
        assertEquals(AuthorizationFlowTrace.FlowStatus.AUTHORIZATION_CODE_ISSUED.name(), flow.getStatus());
        assertEquals("user-john", flow.getUserId());
    }

    @Test
    @DisplayName("Test token exchanged step")
    void testTokenExchanged() {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        String flowId = "flow-token-exchange";

        traceService.startFlow(traceId, flowId, "client1", "192.168.1.1", "TestAgent");
        traceService.tokenExchanged(flowId, "authorization_code");

        AuthorizationFlowTrace flow = traceService.getFlow(flowId);
        assertEquals(AuthorizationFlowTrace.FlowStatus.TOKEN_EXCHANGED.name(), flow.getStatus());
        assertEquals("authorization_code", flow.getGrantType());
    }

    @Test
    @DisplayName("Test completing a flow")
    void testCompleteFlow() {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        String flowId = "flow-complete";

        traceService.startFlow(traceId, flowId, "client1", "192.168.1.1", "TestAgent");
        traceService.authorizationCodeIssued(flowId, "user1");
        traceService.tokenExchanged(flowId, "authorization_code");

        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        traceService.completeFlow(flowId);

        AuthorizationFlowTrace flow = traceService.getFlow(flowId);
        assertEquals(AuthorizationFlowTrace.FlowStatus.COMPLETED.name(), flow.getStatus());
        assertNotNull(flow.getEndTime());
        assertTrue(flow.getDurationMs() >= 10, "Duration should be at least 10ms");
        assertNull(traceService.getActiveFlows().stream()
                .filter(f -> flowId.equals(f.getFlowId()))
                .findFirst()
                .orElse(null));
    }

    @Test
    @DisplayName("Test failing a flow")
    void testFailFlow() {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        String flowId = "flow-fail";

        traceService.startFlow(traceId, flowId, "client1", "192.168.1.1", "TestAgent");
        traceService.failFlow(flowId, "invalid_client", "Client authentication failed");

        AuthorizationFlowTrace flow = traceService.getFlow(flowId);
        assertEquals(AuthorizationFlowTrace.FlowStatus.FAILED.name(), flow.getStatus());
        assertEquals("invalid_client", flow.getErrorCode());
        assertEquals("Client authentication failed", flow.getErrorDescription());
        assertNotNull(flow.getEndTime());
        assertNotNull(flow.getDurationMs());
    }

    @Test
    @DisplayName("Test recording flow steps with attributes")
    void testRecordStep() {
        String traceId = UUID.randomUUID().toString().replace("-", "");
        String flowId = "flow-steps";

        traceService.startFlow(traceId, flowId, "client1", "192.168.1.1", "TestAgent");

        traceService.recordStep(flowId,
                AuthorizationFlowTrace.FlowStep.USER_AUTHENTICATION,
                Map.of("authMethod", "password", "rememberMe", "true"));

        traceService.recordStep(flowId,
                AuthorizationFlowTrace.FlowStep.USER_CONSENT,
                Map.of("scope", "read write", "consentGiven", "true"));

        AuthorizationFlowTrace flow = traceService.getFlow(flowId);
        assertEquals("password", flow.getCustomAttributes().get("authMethod"));
        assertEquals("true", flow.getCustomAttributes().get("rememberMe"));
        assertEquals("read write", flow.getCustomAttributes().get("scope"));
    }

    @Test
    @DisplayName("Test query flows by trace ID")
    void testGetFlowsByTraceId() {
        String traceId = UUID.randomUUID().toString().replace("-", "");

        traceService.startFlow(traceId, "flow-1", "client1", "192.168.1.1", "Agent1");
        traceService.startFlow(traceId, "flow-2", "client2", "192.168.1.2", "Agent2");
        traceService.startFlow("other-trace-id", "flow-3", "client3", "192.168.1.3", "Agent3");

        List<AuthorizationFlowTrace> flows = traceService.getFlowsByTraceId(traceId);
        assertEquals(2, flows.size());
        assertTrue(flows.stream().allMatch(f -> traceId.equals(f.getTraceId())));
    }

    @Test
    @DisplayName("Test get active flows")
    void testGetActiveFlows() {
        traceService.startFlow("trace1", "flow-active-1", "client1", "192.168.1.1", "Agent1");
        traceService.startFlow("trace2", "flow-active-2", "client2", "192.168.1.2", "Agent2");
        traceService.startFlow("trace3", "flow-active-3", "client3", "192.168.1.3", "Agent3");

        traceService.completeFlow("flow-active-2");

        List<AuthorizationFlowTrace> activeFlows = traceService.getActiveFlows();
        assertEquals(2, activeFlows.size());
        assertEquals(2, traceService.getActiveFlowCount());
    }

    @Test
    @DisplayName("Test get failed flows")
    void testGetFailedFlows() {
        for (int i = 0; i < 10; i++) {
            String flowId = "flow-" + i;
            traceService.startFlow("trace-" + i, flowId, "client1", "192.168.1." + i, "Agent");
            if (i < 3) {
                traceService.failFlow(flowId, "error-" + i, "Error description " + i);
            } else {
                traceService.completeFlow(flowId);
            }
        }

        List<AuthorizationFlowTrace> failedFlows = traceService.getFailedFlows(100);
        assertEquals(3, failedFlows.size());
        assertTrue(failedFlows.stream()
                .allMatch(f -> AuthorizationFlowTrace.FlowStatus.FAILED.name().equals(f.getStatus())));
    }

    @Test
    @DisplayName("Test get flow returns null for non-existent flow")
    void testGetNonExistentFlow() {
        assertNull(traceService.getFlow("non-existent-flow"));
    }

    @Test
    @DisplayName("Test operations on non-existent flow don't throw")
    void testOperationsOnNonExistentFlow() {
        assertDoesNotThrow(() -> traceService.authorizationCodeIssued("non-existent", "user1"));
        assertDoesNotThrow(() -> traceService.tokenExchanged("non-existent", "password"));
        assertDoesNotThrow(() -> traceService.completeFlow("non-existent"));
        assertDoesNotThrow(() -> traceService.failFlow("non-existent", "error", "desc"));
        assertDoesNotThrow(() -> traceService.recordStep("non-existent",
                AuthorizationFlowTrace.FlowStep.USER_AUTHENTICATION, Map.of()));
    }

    @Test
    @DisplayName("Test flow duration calculation")
    void testFlowDurationCalculation() throws InterruptedException {
        String flowId = "flow-duration";
        traceService.startFlow("trace-duration", flowId, "client1", "127.0.0.1", "Test");

        Thread.sleep(100);

        traceService.completeFlow(flowId);

        AuthorizationFlowTrace flow = traceService.getFlow(flowId);
        assertTrue(flow.getDurationMs() >= 100, "Duration should be at least 100ms");
        assertTrue(flow.getDurationMs() < 5000, "Duration should be reasonable");
    }
}

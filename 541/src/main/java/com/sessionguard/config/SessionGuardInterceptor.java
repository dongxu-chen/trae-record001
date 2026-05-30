package com.sessionguard.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sessionguard.collector.IpContextCollector;
import com.sessionguard.model.RiskAssessment;
import com.sessionguard.model.ThreatIntel;
import com.sessionguard.service.SessionGuardService;
import com.sessionguard.service.ThreatIntelService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.HashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Slf4j
public class SessionGuardInterceptor implements HandlerInterceptor {

    private final SessionGuardService sessionGuardService;
    private final ThreatIntelService threatIntelService;
    private final IpContextCollector ipContextCollector;
    private final ObjectMapper objectMapper;

    private static final String SESSION_HEADER = "X-Session-Id";
    private static final String SCENARIO_HEADER = "X-Business-Scenario";

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }

        String clientIp = ipContextCollector.collect(request).getIpAddress();
        ThreatIntel threat = threatIntelService.checkIpThreat(clientIp);
        if (threat != null && threat.isActive() && threat.getSeverity().ordinal() >= ThreatIntel.ThreatSeverity.HIGH.ordinal()) {
            log.warn("ThreatIntel blocked request: ip={}, type={}, severity={}, path={}",
                    clientIp, threat.getThreatType(), threat.getSeverity(), request.getRequestURI());

            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");

            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("success", false);
            errorBody.put("message", "Access denied: IP blocked due to security policy");
            errorBody.put("blocked", true);
            errorBody.put("threatType", threat.getThreatType().name());
            errorBody.put("threatSeverity", threat.getSeverity().name());
            errorBody.put("threatDescription", threat.getDescription());

            Map<String, Object> guidance = new HashMap<>();
            guidance.put("friendlyMessage", "检测到异常访问来源，为保障系统安全已临时限制访问");
            guidance.put("supportContact", "如您认为这是误判，请联系客服：400-XXX-XXXX");
            errorBody.put("userGuidance", guidance);

            response.getWriter().write(objectMapper.writeValueAsString(errorBody));
            return false;
        }

        String sessionId = request.getHeader(SESSION_HEADER);
        if (sessionId == null || sessionId.isBlank()) {
            return true;
        }

        String businessScenario = request.getHeader(SCENARIO_HEADER);
        var assessment = sessionGuardService.verifySession(sessionId, request, businessScenario);

        if (assessment.getRiskLevel().ordinal() >= RiskAssessment.RiskLevel.HIGH.ordinal()) {
            log.warn("SessionGuard blocked request: sessionId={}, risk={}, scenario={}, path={}",
                    sessionId, assessment.getTotalScore(), businessScenario, request.getRequestURI());

            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");

            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("success", false);
            errorBody.put("message", "Session risk too high: " + assessment.getRiskLevel());
            errorBody.put("riskScore", assessment.getTotalScore());
            errorBody.put("riskLevel", assessment.getRiskLevel().name());

            if (assessment.getUserGuidance() != null) {
                Map<String, Object> guidance = new HashMap<>();
                guidance.put("friendlyMessage", assessment.getUserGuidance().getFriendlyMessage());
                guidance.put("reauthUrl", assessment.getUserGuidance().getReauthUrl());
                guidance.put("supportContact", assessment.getUserGuidance().getSupportContact());
                errorBody.put("userGuidance", guidance);
            }

            if (assessment.getExtendedDetectionInfo() != null) {
                errorBody.put("detectionDetails", assessment.getExtendedDetectionInfo());
            }

            response.getWriter().write(objectMapper.writeValueAsString(errorBody));
            return false;
        }

        request.setAttribute("riskAssessment", assessment);
        return true;
    }
}

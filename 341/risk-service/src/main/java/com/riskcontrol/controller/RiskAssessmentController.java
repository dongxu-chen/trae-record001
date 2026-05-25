package com.riskcontrol.controller;

import com.riskcontrol.common.model.RiskAssessmentResult;
import com.riskcontrol.common.model.RiskEvent;
import com.riskcontrol.service.RiskAssessmentService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/risk")
public class RiskAssessmentController {

    private static final Logger logger = LoggerFactory.getLogger(RiskAssessmentController.class);

    private final RiskAssessmentService riskAssessmentService;

    @Autowired
    public RiskAssessmentController(RiskAssessmentService riskAssessmentService) {
        this.riskAssessmentService = riskAssessmentService;
    }

    @PostMapping("/assess/login")
    public ResponseEntity<RiskAssessmentResult> assessLogin(
            @RequestBody RiskEvent event,
            HttpServletRequest request) {
        enrichEventFromRequest(event, request);
        logger.info("Received login risk assessment request for user: {}", event.getUserId());
        RiskAssessmentResult result = riskAssessmentService.assessLoginRisk(event);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/assess/register")
    public ResponseEntity<RiskAssessmentResult> assessRegister(
            @RequestBody RiskEvent event,
            HttpServletRequest request) {
        enrichEventFromRequest(event, request);
        logger.info("Received register risk assessment request for account: {}", event.getAccount());
        RiskAssessmentResult result = riskAssessmentService.assessRegisterRisk(event);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/assess/password-change")
    public ResponseEntity<RiskAssessmentResult> assessPasswordChange(
            @RequestBody RiskEvent event,
            HttpServletRequest request) {
        enrichEventFromRequest(event, request);
        logger.info("Received password change risk assessment request for user: {}", event.getUserId());
        RiskAssessmentResult result = riskAssessmentService.assessPasswordChangeRisk(event);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/assess")
    public ResponseEntity<RiskAssessmentResult> assessGeneric(
            @RequestBody RiskEvent event,
            HttpServletRequest request) {
        enrichEventFromRequest(event, request);
        logger.info("Received generic risk assessment request, event type: {}", event.getEventType());
        RiskAssessmentResult result = riskAssessmentService.assessRisk(event);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "UP");
        health.put("service", "risk-control-system");
        health.put("timestamp", System.currentTimeMillis());
        return ResponseEntity.ok(health);
    }

    @GetMapping("/event/{eventId}")
    public ResponseEntity<RiskEvent> getEvent(@PathVariable String eventId) {
        logger.debug("Received request for event: {}", eventId);
        RiskEvent event = RiskEvent.builder()
                .eventId(eventId)
                .build();
        return ResponseEntity.ok(event);
    }

    private void enrichEventFromRequest(RiskEvent event, HttpServletRequest request) {
        if (event.getEventId() == null || event.getEventId().isEmpty()) {
            event.setEventId(UUID.randomUUID().toString());
        }

        if (event.getEventTimestamp() == 0) {
            event.setEventTimestamp(System.currentTimeMillis());
        }

        if (event.getIpAddress() == null || event.getIpAddress().isEmpty()) {
            String clientIp = getClientIpAddress(request);
            event.setIpAddress(clientIp);
        }

        if (event.getUserAgent() == null || event.getUserAgent().isEmpty()) {
            event.setUserAgent(request.getHeader("User-Agent"));
        }

        if (event.getReferer() == null || event.getReferer().isEmpty()) {
            event.setReferer(request.getHeader("Referer"));
        }

        if (event.getSessionId() == null || event.getSessionId().isEmpty()) {
            event.setSessionId(request.getSession().getId());
        }
    }

    private String getClientIpAddress(HttpServletRequest request) {
        String[] headers = {
                "X-Forwarded-For",
                "X-Real-IP",
                "X-Cluster-Client-Ip",
                "X-Forwarded",
                "Forwarded-For",
                "Forwarded",
                "Proxy-Client-IP",
                "WL-Proxy-Client-IP",
                "HTTP_CLIENT_IP",
                "HTTP_X_FORWARDED_FOR"
        };

        for (String header : headers) {
            String ip = request.getHeader(header);
            if (ip != null && !ip.isEmpty() && !"unknown".equalsIgnoreCase(ip)) {
                if (ip.contains(",")) {
                    return ip.split(",")[0].trim();
                }
                return ip.trim();
            }
        }

        return request.getRemoteAddr();
    }
}

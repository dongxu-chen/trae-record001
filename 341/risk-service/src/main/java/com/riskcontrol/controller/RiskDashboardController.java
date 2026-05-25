package com.riskcontrol.controller;

import com.riskcontrol.common.model.RiskAssessmentResult;
import com.riskcontrol.common.model.RiskEvent;
import com.riskcontrol.service.RiskDashboardService;
import com.riskcontrol.service.RiskSandboxService;
import com.riskcontrol.service.RiskSandboxService.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/dashboard")
public class RiskDashboardController {

    private static final Logger logger = LoggerFactory.getLogger(RiskDashboardController.class);

    private final RiskDashboardService dashboardService;
    private final RiskSandboxService sandboxService;

    @Autowired
    public RiskDashboardController(RiskDashboardService dashboardService,
                                    RiskSandboxService sandboxService) {
        this.dashboardService = dashboardService;
        this.sandboxService = sandboxService;
    }

    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> getSummary() {
        logger.debug("Getting dashboard summary");
        Map<String, Object> summary = dashboardService.getDashboardSummary();
        return ResponseEntity.ok(summary);
    }

    @GetMapping("/trend")
    public ResponseEntity<Map<String, Object>> getTrendData(
            @RequestParam(defaultValue = "24") int hours) {
        logger.debug("Getting trend data for {} hours", hours);
        hours = Math.min(Math.max(hours, 1), 168);
        Map<String, Object> trend = dashboardService.getTrendData(hours);
        return ResponseEntity.ok(trend);
    }

    @GetMapping("/events/recent")
    public ResponseEntity<List<Map<String, Object>>> getRecentEvents(
            @RequestParam(defaultValue = "100") int limit) {
        logger.debug("Getting recent events, limit: {}", limit);
        limit = Math.min(Math.max(limit, 1), 1000);
        List<Map<String, Object>> events = dashboardService.getRecentEvents(limit);
        return ResponseEntity.ok(events);
    }

    @GetMapping("/distribution")
    public ResponseEntity<Map<String, Object>> getRiskDistribution() {
        logger.debug("Getting risk distribution");
        Map<String, Object> distribution = dashboardService.getRiskDistribution();
        return ResponseEntity.ok(distribution);
    }

    @GetMapping("/disposition")
    public ResponseEntity<Map<String, Object>> getDispositionStats() {
        logger.debug("Getting disposition statistics");
        Map<String, Object> stats = dashboardService.getDispositionStats();
        return ResponseEntity.ok(stats);
    }

    @PostMapping("/reset")
    public ResponseEntity<Map<String, Object>> resetDashboard() {
        logger.warn("Resetting dashboard statistics");
        dashboardService.resetDashboard();
        Map<String, Object> response = new java.util.HashMap<>();
        response.put("success", true);
        response.put("message", "Dashboard statistics reset successfully");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/sandbox/simulate")
    public ResponseEntity<SandboxResult> simulateAssessment(
            @RequestBody Map<String, Object> request) {

        RiskEvent event = parseEventFromRequest(request);
        SandboxConfig config = parseConfigFromRequest(request);

        logger.info("Sandbox simulation request for event type: {}", event.getEventType());

        SandboxResult result = sandboxService.simulateAssessment(event, config);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/sandbox/batch")
    public ResponseEntity<SandboxResult> batchSimulate(
            @RequestBody Map<String, Object> request) {

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> eventsData = (List<Map<String, Object>>) request.get("events");
        SandboxConfig config = parseConfigFromRequest(request);

        logger.info("Batch sandbox simulation request, {} events", eventsData.size());

        List<RiskEvent> events = new java.util.ArrayList<>();
        for (Map<String, Object> eventData : eventsData) {
            events.add(parseEventFromRequest(eventData));
        }

        SandboxResult result = sandboxService.batchSimulate(events, config);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/sandbox/whatif")
    public ResponseEntity<SandboxResult> whatIfAnalysis(
            @RequestBody Map<String, Object> request) {

        RiskEvent event = parseEventFromRequest(request);
        SandboxConfig config = parseConfigFromRequest(request);
        config.setShowWhatIf(true);

        logger.info("What-if analysis request for event: {}", event.getEventId());

        SandboxResult result = sandboxService.simulateAssessment(event, config);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/sandbox/templates")
    public ResponseEntity<Map<String, Object>> getSandboxTemplates() {
        Map<String, Object> templates = new java.util.HashMap<>();

        Map<String, Object> normalLogin = new java.util.HashMap<>();
        normalLogin.put("name", "正常登录");
        normalLogin.put("description", "模拟正常用户登录");
        normalLogin.put("eventType", "LOGIN");
        normalLogin.put("ipInfo", Map.of("isProxy", false, "isVpn", false, "isTor", false));
        normalLogin.put("loginAttemptCount", 0);
        templates.put("normal_login", normalLogin);

        Map<String, Object> vpnLogin = new java.util.HashMap<>();
        vpnLogin.put("name", "VPN登录");
        vpnLogin.put("description", "使用VPN的登录尝试");
        vpnLogin.put("eventType", "LOGIN");
        vpnLogin.put("ipInfo", Map.of("isProxy", true, "isVpn", true, "isTor", false));
        vpnLogin.put("loginAttemptCount", 1);
        templates.put("vpn_login", vpnLogin);

        Map<String, Object> bruteForce = new java.util.HashMap<>();
        bruteForce.put("name", "暴力破解");
        bruteForce.put("description", "多次失败后的登录尝试");
        bruteForce.put("eventType", "LOGIN");
        bruteForce.put("loginAttemptCount", 8);
        bruteForce.put("velocityKmPerHour", 0);
        templates.put("brute_force", bruteForce);

        Map<String, Object> impossibleTravel = new java.util.HashMap<>();
        impossibleTravel.put("name", "不可能旅行");
        impossibleTravel.put("description", "短时间内跨越大距离");
        impossibleTravel.put("eventType", "LOGIN");
        impossibleTravel.put("velocityKmPerHour", 1500);
        templates.put("impossible_travel", impossibleTravel);

        Map<String, Object> torLogin = new java.util.HashMap<>();
        torLogin.put("name", "TOR网络登录");
        torLogin.put("description", "使用TOR网络的登录");
        torLogin.put("eventType", "LOGIN");
        torLogin.put("ipInfo", Map.of("isProxy", true, "isVpn", false, "isTor", true));
        templates.put("tor_login", torLogin);

        Map<String, Object> suspiciousRegister = new java.util.HashMap<>();
        suspiciousRegister.put("name", "可疑注册");
        suspiciousRegister.put("description", "使用临时邮箱的注册");
        suspiciousRegister.put("eventType", "REGISTER");
        suspiciousRegister.put("email", "test@tempmail.com");
        suspiciousRegister.put("ipInfo", Map.of("isProxy", true, "isVpn", true));
        templates.put("suspicious_register", suspiciousRegister);

        return ResponseEntity.ok(templates);
    }

    private RiskEvent parseEventFromRequest(Map<String, Object> request) {
        RiskEvent event = new RiskEvent();

        if (request.containsKey("event")) {
            @SuppressWarnings("unchecked")
            Map<String, Object> eventData = (Map<String, Object>) request.get("event");
            parseEventData(event, eventData);
        } else {
            parseEventData(event, request);
        }

        return event;
    }

    private void parseEventData(RiskEvent event, Map<String, Object> data) {
        if (data.get("eventId") != null) event.setEventId((String) data.get("eventId"));
        if (data.get("userId") != null) event.setUserId((String) data.get("userId"));
        if (data.get("account") != null) event.setAccount((String) data.get("account"));
        if (data.get("eventType") != null) {
            event.setEventType(com.riskcontrol.common.enums.EventType.valueOf((String) data.get("eventType")));
        }
        if (data.get("ipAddress") != null) event.setIpAddress((String) data.get("ipAddress"));
        if (data.get("userAgent") != null) event.setUserAgent((String) data.get("userAgent"));
        if (data.get("email") != null) event.setEmail((String) data.get("email"));
        if (data.get("phone") != null) event.setPhone((String) data.get("phone"));
        if (data.get("loginAttemptCount") != null) {
            event.setLoginAttemptCount(((Number) data.get("loginAttemptCount")).intValue());
        }
        if (data.get("velocityKmPerHour") != null) {
            event.setVelocityKmPerHour(((Number) data.get("velocityKmPerHour")).doubleValue());
        }

        if (data.get("ipInfo") != null) {
            @SuppressWarnings("unchecked")
            Map<String, Object> ipInfoData = (Map<String, Object>) data.get("ipInfo");
            com.riskcontrol.common.model.IpInfo ipInfo = new com.riskcontrol.common.model.IpInfo();
            if (ipInfoData.get("ipAddress") != null) ipInfo.setIpAddress((String) ipInfoData.get("ipAddress"));
            if (ipInfoData.get("country") != null) ipInfo.setCountry((String) ipInfoData.get("country"));
            if (ipInfoData.get("latitude") != null) ipInfo.setLatitude(((Number) ipInfoData.get("latitude")).doubleValue());
            if (ipInfoData.get("longitude") != null) ipInfo.setLongitude(((Number) ipInfoData.get("longitude")).doubleValue());
            if (ipInfoData.get("isp") != null) ipInfo.setIsp((String) ipInfoData.get("isp"));
            if (ipInfoData.get("isProxy") != null) ipInfo.setProxy((Boolean) ipInfoData.get("isProxy"));
            if (ipInfoData.get("isVpn") != null) ipInfo.setVpn((Boolean) ipInfoData.get("isVpn"));
            if (ipInfoData.get("isTor") != null) ipInfo.setTor((Boolean) ipInfoData.get("isTor"));
            if (ipInfoData.get("isDataCenter") != null) ipInfo.setDataCenter((Boolean) ipInfoData.get("isDataCenter"));
            if (ipInfoData.get("isBlacklisted") != null) ipInfo.setBlacklisted((Boolean) ipInfoData.get("isBlacklisted"));
            if (ipInfoData.get("riskScore") != null) ipInfo.setRiskScore(((Number) ipInfoData.get("riskScore")).intValue());
            event.setIpInfo(ipInfo);
        }

        if (data.get("deviceFingerprint") != null) {
            @SuppressWarnings("unchecked")
            Map<String, Object> deviceData = (Map<String, Object>) data.get("deviceFingerprint");
            com.riskcontrol.common.model.DeviceFingerprint device = new com.riskcontrol.common.model.DeviceFingerprint();
            if (deviceData.get("deviceId") != null) device.setDeviceId((String) deviceData.get("deviceId"));
            if (deviceData.get("userAgent") != null) device.setUserAgent((String) deviceData.get("userAgent"));
            if (deviceData.get("browser") != null) device.setBrowser((String) deviceData.get("browser"));
            if (deviceData.get("os") != null) device.setOs((String) deviceData.get("os"));
            if (deviceData.get("platform") != null) device.setPlatform((String) deviceData.get("platform"));
            if (deviceData.get("canvasFingerprint") != null) device.setCanvasFingerprint((String) deviceData.get("canvasFingerprint"));
            if (deviceData.get("webglFingerprint") != null) device.setWebglFingerprint((String) deviceData.get("webglFingerprint"));
            if (deviceData.get("fontsFingerprint") != null) device.setFontsFingerprint((String) deviceData.get("fontsFingerprint"));
            if (deviceData.get("associationCount") != null) device.setAssociationCount(((Number) deviceData.get("associationCount")).intValue());
            event.setDeviceFingerprint(device);
        }
    }

    private SandboxConfig parseConfigFromRequest(Map<String, Object> request) {
        SandboxConfig config = new SandboxConfig();

        if (request.get("config") != null) {
            @SuppressWarnings("unchecked")
            Map<String, Object> configData = (Map<String, Object>) request.get("config");

            if (configData.get("userId") != null) config.setUserId((String) configData.get("userId"));
            if (configData.get("enableML") != null) config.setEnableML((Boolean) configData.get("enableML"));
            if (configData.get("showComparison") != null) config.setShowComparison((Boolean) configData.get("showComparison"));
            if (configData.get("showWhatIf") != null) config.setShowWhatIf((Boolean) configData.get("showWhatIf"));
            if (configData.get("baselineScore") != null) config.setBaselineScore(((Number) configData.get("baselineScore")).intValue());
            if (configData.get("accountAgeDays") != null) config.setAccountAgeDays(((Number) configData.get("accountAgeDays")).intValue());
            if (configData.get("fraudFlagCount") != null) config.setFraudFlagCount(((Number) configData.get("fraudFlagCount")).intValue());
            if (configData.get("failedLoginCount") != null) config.setFailedLoginCount(((Number) configData.get("failedLoginCount")).intValue());
            if (configData.get("commonIp") != null) config.setCommonIp((String) configData.get("commonIp"));
            if (configData.get("commonDeviceId") != null) config.setCommonDeviceId((String) configData.get("commonDeviceId"));
            if (configData.get("commonCountry") != null) config.setCommonCountry((String) configData.get("commonCountry"));
            if (configData.get("whatIfScenarios") != null) {
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> scenarios = (List<Map<String, Object>>) configData.get("whatIfScenarios");
                config.setWhatIfScenarios(scenarios);
            }
        }

        return config;
    }
}

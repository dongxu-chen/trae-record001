package com.riskcontrol.controller;

import com.riskcontrol.ml.config.RiskWeightConfig;
import com.riskcontrol.ml.config.RiskWeightConfig.SceneWeight;
import com.riskcontrol.ml.engine.MLScoringService;
import com.riskcontrol.redis.service.IpBlacklistService;
import com.riskcontrol.service.ProxyIpUpdateService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/admin")
public class RiskAdminController {

    private static final Logger logger = LoggerFactory.getLogger(RiskAdminController.class);

    private final IpBlacklistService ipBlacklistService;
    private final MLScoringService mlScoringService;
    private final ProxyIpUpdateService proxyIpUpdateService;

    @Autowired
    public RiskAdminController(IpBlacklistService ipBlacklistService,
                               MLScoringService mlScoringService,
                               ProxyIpUpdateService proxyIpUpdateService) {
        this.ipBlacklistService = ipBlacklistService;
        this.mlScoringService = mlScoringService;
        this.proxyIpUpdateService = proxyIpUpdateService;
    }

    @PostMapping("/ip/blacklist")
    public ResponseEntity<Map<String, Object>> addToBlacklist(
            @RequestParam String ipAddress,
            @RequestParam(required = false, defaultValue = "manual") String reason) {
        logger.info("Admin adding IP to blacklist: {}, reason: {}", ipAddress, reason);
        ipBlacklistService.addToBlacklist(ipAddress, reason);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "IP added to blacklist");
        response.put("ipAddress", ipAddress);
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/ip/blacklist")
    public ResponseEntity<Map<String, Object>> removeFromBlacklist(
            @RequestParam String ipAddress) {
        logger.info("Admin removing IP from blacklist: {}", ipAddress);
        ipBlacklistService.removeFromBlacklist(ipAddress);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "IP removed from blacklist");
        response.put("ipAddress", ipAddress);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/ip/check")
    public ResponseEntity<Map<String, Object>> checkIp(@RequestParam String ipAddress) {
        logger.debug("Checking IP status: {}", ipAddress);
        Map<String, Object> response = new HashMap<>();
        response.put("ipAddress", ipAddress);
        response.put("isBlacklisted", ipBlacklistService.isBlacklisted(ipAddress));
        response.put("isProxy", ipBlacklistService.isProxyIp(ipAddress));
        response.put("proxyType", ipBlacklistService.getProxyType(ipAddress));
        response.put("riskScore", ipBlacklistService.getIpRiskScore(ipAddress));
        return ResponseEntity.ok(response);
    }

    @PostMapping("/proxy/add")
    public ResponseEntity<Map<String, Object>> addProxyIp(
            @RequestParam String ipAddress,
            @RequestParam(defaultValue = "proxy") String proxyType,
            @RequestParam(defaultValue = "25") int riskScore) {
        logger.info("Admin adding proxy IP: {}, type: {}, score: {}", ipAddress, proxyType, riskScore);
        ipBlacklistService.addProxyIp(ipAddress, proxyType, riskScore);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Proxy IP added");
        response.put("ipAddress", ipAddress);
        response.put("proxyType", proxyType);
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/proxy/remove")
    public ResponseEntity<Map<String, Object>> removeProxyIp(
            @RequestParam String ipAddress,
            @RequestParam(defaultValue = "proxy") String proxyType) {
        logger.info("Admin removing proxy IP: {}, type: {}", ipAddress, proxyType);
        ipBlacklistService.removeProxyIp(ipAddress, proxyType);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Proxy IP removed");
        response.put("ipAddress", ipAddress);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/proxy/update")
    public ResponseEntity<Map<String, Object>> triggerProxyUpdate() {
        logger.info("Admin triggering proxy IP update");
        Map<String, Object> response = new HashMap<>();
        try {
            proxyIpUpdateService.manualUpdate();
            response.put("success", true);
            response.put("message", "Proxy IP update triggered");
            response.put("stats", ipBlacklistService.getProxyStats());
        } catch (Exception e) {
            logger.error("Proxy IP update failed", e);
            response.put("success", false);
            response.put("error", e.getMessage());
        }
        return ResponseEntity.ok(response);
    }

    @GetMapping("/proxy/stats")
    public ResponseEntity<Map<String, Object>> getProxyStats() {
        Map<String, Object> response = new HashMap<>();
        response.put("stats", ipBlacklistService.getProxyStats());
        response.put("totalProxyCount", ipBlacklistService.getTotalProxyCount());
        response.put("lastUpdateTimestamp", ipBlacklistService.getLastProxyUpdateTimestamp());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/ml/status")
    public ResponseEntity<Map<String, Object>> getMLStatus() {
        Map<String, Object> response = new HashMap<>();
        response.put("modelReady", mlScoringService.isModelReady());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/ml/reload")
    public ResponseEntity<Map<String, Object>> reloadMLModel() {
        logger.info("Admin requesting ML model reload");
        Map<String, Object> response = new HashMap<>();
        try {
            mlScoringService.reloadModel();
            response.put("success", true);
            response.put("message", "ML model reloaded successfully");
            response.put("modelReady", mlScoringService.isModelReady());
        } catch (Exception e) {
            logger.error("Failed to reload ML model", e);
            response.put("success", false);
            response.put("error", e.getMessage());
        }
        return ResponseEntity.ok(response);
    }

    @GetMapping("/weights")
    public ResponseEntity<Map<String, Object>> getWeights() {
        Map<String, Object> response = new HashMap<>();
        RiskWeightConfig config = mlScoringService.getWeightConfig();
        response.put("defaultRuleWeight", config.getRuleWeight());
        response.put("defaultMlWeight", config.getMlWeight());
        response.put("highRiskThreshold", config.getHighRiskThreshold());
        response.put("conservationFactor", config.getHighRiskConservationFactor());

        Map<String, Map<String, Object>> sceneWeights = new HashMap<>();
        for (Map.Entry<String, SceneWeight> entry : config.getSceneWeights().entrySet()) {
            Map<String, Object> scene = new HashMap<>();
            scene.put("ruleWeight", entry.getValue().getRuleWeight());
            scene.put("mlWeight", entry.getValue().getMlWeight());
            scene.put("highRiskThreshold", entry.getValue().getHighRiskThreshold());
            scene.put("conservationFactor", entry.getValue().getConservationFactor());
            sceneWeights.put(entry.getKey(), scene);
        }
        response.put("sceneWeights", sceneWeights);
        return ResponseEntity.ok(response);
    }

    @PutMapping("/weights/scene/{scene}")
    public ResponseEntity<Map<String, Object>> updateSceneWeight(
            @PathVariable String scene,
            @RequestParam double ruleWeight,
            @RequestParam double mlWeight,
            @RequestParam(defaultValue = "70") int highRiskThreshold,
            @RequestParam(defaultValue = "0.9") double conservationFactor) {

        logger.info("Admin updating scene weight for {}: ruleWeight={}, mlWeight={}", scene, ruleWeight, mlWeight);
        mlScoringService.updateSceneWeight(scene, ruleWeight, mlWeight, highRiskThreshold, conservationFactor);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Scene weight updated successfully");
        response.put("scene", scene);
        response.put("ruleWeight", ruleWeight);
        response.put("mlWeight", mlWeight);
        response.put("highRiskThreshold", highRiskThreshold);
        response.put("conservationFactor", conservationFactor);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/weights/scene/{scene}")
    public ResponseEntity<Map<String, Object>> getSceneWeight(@PathVariable String scene) {
        SceneWeight weight = mlScoringService.getWeightConfig().getSceneWeight(scene);
        Map<String, Object> response = new HashMap<>();
        response.put("scene", scene);
        response.put("ruleWeight", weight.getRuleWeight());
        response.put("mlWeight", weight.getMlWeight());
        response.put("highRiskThreshold", weight.getHighRiskThreshold());
        response.put("conservationFactor", weight.getConservationFactor());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("mlModelReady", mlScoringService.isModelReady());
        stats.put("totalProxyIps", ipBlacklistService.getTotalProxyCount());
        stats.put("proxyStats", ipBlacklistService.getProxyStats());
        stats.put("lastProxyUpdate", ipBlacklistService.getLastProxyUpdateTimestamp());
        stats.put("timestamp", System.currentTimeMillis());
        return ResponseEntity.ok(stats);
    }
}

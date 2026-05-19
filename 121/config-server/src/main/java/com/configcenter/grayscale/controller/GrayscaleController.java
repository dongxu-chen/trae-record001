package com.configcenter.grayscale.controller;

import com.configcenter.grayscale.entity.GrayscaleRule;
import com.configcenter.grayscale.service.GrayscaleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/grayscale")
public class GrayscaleController {

    @Autowired
    private GrayscaleService grayscaleService;

    @PostMapping("/rules")
    public ResponseEntity<GrayscaleRule> createRule(@RequestBody GrayscaleRuleRequest request) {
        GrayscaleRule rule = new GrayscaleRule();
        rule.setServiceName(request.getServiceName());
        rule.setProfile(request.getProfile());
        rule.setLabel(request.getLabel());
        rule.setType(request.getType());
        rule.setTargetIps(request.getTargetIps());
        rule.setTargetInstances(request.getTargetInstances());
        rule.setPercentage(request.getPercentage());
        rule.setDescription(request.getDescription());

        GrayscaleRule created = grayscaleService.createRule(rule, request.getCreatedBy());
        return ResponseEntity.ok(created);
    }

    @GetMapping("/rules")
    public ResponseEntity<List<GrayscaleRule>> getRules(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) GrayscaleRule.GrayscaleStatus status) {
        List<GrayscaleRule> rules;
        if (serviceName != null) {
            rules = grayscaleService.getRulesByService(serviceName);
        } else {
            rules = grayscaleService.getAllRules();
        }
        return ResponseEntity.ok(rules);
    }

    @GetMapping("/rules/{id}")
    public ResponseEntity<GrayscaleRule> getRule(@PathVariable String id) {
        return grayscaleService.getRule(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PutMapping("/rules/{id}/activate")
    public ResponseEntity<GrayscaleRule> activateRule(@PathVariable String id) {
        GrayscaleRule rule = grayscaleService.activateRule(id);
        return ResponseEntity.ok(rule);
    }

    @PutMapping("/rules/{id}/pause")
    public ResponseEntity<GrayscaleRule> pauseRule(@PathVariable String id) {
        GrayscaleRule rule = grayscaleService.pauseRule(id);
        return ResponseEntity.ok(rule);
    }

    @PutMapping("/rules/{id}/complete")
    public ResponseEntity<GrayscaleRule> completeRule(@PathVariable String id) {
        GrayscaleRule rule = grayscaleService.completeRule(id);
        return ResponseEntity.ok(rule);
    }

    @DeleteMapping("/rules/{id}")
    public ResponseEntity<Map<String, Object>> deleteRule(@PathVariable String id) {
        grayscaleService.deleteRule(id);
        Map<String, Object> result = new HashMap<>();
        result.put("status", "success");
        result.put("message", "Rule deleted: " + id);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/check")
    public ResponseEntity<Map<String, Object>> checkGrayscaleEligibility(
            @RequestParam String serviceName,
            @RequestParam(required = false) String ip,
            @RequestParam(required = false) String instanceId) {
        boolean eligible = grayscaleService.isTargetForGrayscale(serviceName, ip, instanceId);
        Map<String, Object> result = new HashMap<>();
        result.put("serviceName", serviceName);
        result.put("eligibleForGrayscale", eligible);
        result.put("ip", ip);
        result.put("instanceId", instanceId);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getGrayscaleStatus() {
        return ResponseEntity.ok(grayscaleService.getGrayscaleStatus());
    }

    public static class GrayscaleRuleRequest {
        private String serviceName;
        private String profile;
        private String label;
        private GrayscaleRule.RuleType type;
        private List<String> targetIps;
        private List<String> targetInstances;
        private Integer percentage;
        private String description;
        private String createdBy;

        public String getServiceName() { return serviceName; }
        public void setServiceName(String serviceName) { this.serviceName = serviceName; }
        public String getProfile() { return profile; }
        public void setProfile(String profile) { this.profile = profile; }
        public String getLabel() { return label; }
        public void setLabel(String label) { this.label = label; }
        public GrayscaleRule.RuleType getType() { return type; }
        public void setType(GrayscaleRule.RuleType type) { this.type = type; }
        public List<String> getTargetIps() { return targetIps; }
        public void setTargetIps(List<String> targetIps) { this.targetIps = targetIps; }
        public List<String> getTargetInstances() { return targetInstances; }
        public void setTargetInstances(List<String> targetInstances) { this.targetInstances = targetInstances; }
        public Integer getPercentage() { return percentage; }
        public void setPercentage(Integer percentage) { this.percentage = percentage; }
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        public String getCreatedBy() { return createdBy; }
        public void setCreatedBy(String createdBy) { this.createdBy = createdBy; }
    }
}

package com.configcenter.server.controller;

import com.configcenter.server.entity.GrayRelease;
import com.configcenter.server.service.GrayReleaseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/config/gray")
public class GrayReleaseController {

    @Autowired
    private GrayReleaseService grayReleaseService;

    @PostMapping
    public ResponseEntity<GrayRelease> createGrayRelease(@RequestBody Map<String, Object> request,
                                                          HttpServletRequest httpRequest) {
        Integer percentage = request.get("grayPercentage") != null
                ? Integer.valueOf(request.get("grayPercentage").toString())
                : null;

        GrayRelease grayRelease = grayReleaseService.createGrayRelease(
                (String) request.get("application"),
                (String) request.get("profile"),
                (String) request.get("label"),
                (String) request.get("configContent"),
                GrayRelease.GrayStrategy.valueOf((String) request.get("strategy")),
                (String) request.get("grayIps"),
                percentage,
                (String) request.get("podLabelSelector"),
                (String) request.getOrDefault("createdBy", "system"),
                httpRequest
        );
        return ResponseEntity.ok(grayRelease);
    }

    @PostMapping("/{id}/approve")
    public ResponseEntity<GrayRelease> approveGrayRelease(@PathVariable Long id,
                                                           @RequestParam(defaultValue = "system") String approvedBy,
                                                           HttpServletRequest httpRequest) {
        GrayRelease grayRelease = grayReleaseService.approveGrayRelease(id, approvedBy, httpRequest);
        return ResponseEntity.ok(grayRelease);
    }

    @PostMapping("/{id}/reject")
    public ResponseEntity<GrayRelease> rejectGrayRelease(@PathVariable Long id,
                                                          @RequestParam(defaultValue = "system") String rejectedBy,
                                                          HttpServletRequest httpRequest) {
        GrayRelease grayRelease = grayReleaseService.rejectGrayRelease(id, rejectedBy, httpRequest);
        return ResponseEntity.ok(grayRelease);
    }

    @PostMapping("/{id}/full-release")
    public ResponseEntity<GrayRelease> fullRelease(@PathVariable Long id,
                                                    @RequestParam(defaultValue = "system") String operator,
                                                    HttpServletRequest httpRequest) {
        GrayRelease grayRelease = grayReleaseService.fullRelease(id, operator, httpRequest);
        return ResponseEntity.ok(grayRelease);
    }

    @PostMapping("/{id}/rollback")
    public ResponseEntity<GrayRelease> rollbackGrayRelease(@PathVariable Long id,
                                                            @RequestParam(defaultValue = "system") String operator,
                                                            HttpServletRequest httpRequest) {
        GrayRelease grayRelease = grayReleaseService.rollbackGrayRelease(id, operator, httpRequest);
        return ResponseEntity.ok(grayRelease);
    }

    @GetMapping("/active")
    public ResponseEntity<List<GrayRelease>> getActiveAndPendingGrayReleases() {
        List<GrayRelease> grayReleases = grayReleaseService.getActiveAndPendingGrayReleases();
        return ResponseEntity.ok(grayReleases);
    }

    @GetMapping("/application/{application}")
    public ResponseEntity<List<GrayRelease>> getGrayReleaseHistory(
            @PathVariable String application) {
        List<GrayRelease> grayReleases = grayReleaseService.getGrayReleaseHistory(application);
        return ResponseEntity.ok(grayReleases);
    }

    @GetMapping("/{id}")
    public ResponseEntity<GrayRelease> getGrayRelease(@PathVariable Long id) {
        Optional<GrayRelease> grayRelease = grayReleaseService.getGrayRelease(id);
        return grayRelease.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/active/check")
    public ResponseEntity<Map<String, Object>> checkGrayRequest(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label,
            @RequestParam String clientIp) {
        boolean isGray = grayReleaseService.isGrayRequest(application, profile, label, clientIp);
        return ResponseEntity.ok(Map.of("isGray", isGray, "application", application));
    }
}

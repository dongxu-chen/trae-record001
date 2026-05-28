package com.configcenter.server.controller;

import com.configcenter.server.entity.ConfigVersion;
import com.configcenter.server.service.ConfigVersionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/config/versions")
public class ConfigVersionController {

    @Autowired
    private ConfigVersionService versionService;

    @PostMapping
    public ResponseEntity<ConfigVersion> createVersion(@RequestBody Map<String, String> request,
                                                        HttpServletRequest httpRequest) {
        ConfigVersion version = versionService.createVersion(
                request.get("application"),
                request.get("profile"),
                request.get("label"),
                request.get("configContent"),
                request.get("changeSummary"),
                request.getOrDefault("operator", "system"),
                httpRequest
        );
        return ResponseEntity.ok(version);
    }

    @PostMapping("/{id}/publish")
    public ResponseEntity<ConfigVersion> publishVersion(@PathVariable Long id,
                                                         @RequestParam(defaultValue = "system") String operator,
                                                         HttpServletRequest httpRequest) {
        ConfigVersion version = versionService.publishVersion(id, operator, httpRequest);
        return ResponseEntity.ok(version);
    }

    @PostMapping("/{id}/rollback")
    public ResponseEntity<ConfigVersion> rollback(@PathVariable Long id,
                                                    @RequestParam(defaultValue = "system") String operator,
                                                    HttpServletRequest httpRequest) {
        ConfigVersion version = versionService.rollback(id, operator, httpRequest);
        return ResponseEntity.ok(version);
    }

    @GetMapping("/history")
    public ResponseEntity<List<ConfigVersion>> getVersionHistory(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label) {
        List<ConfigVersion> versions = versionService.getVersionHistory(application, profile, label);
        return ResponseEntity.ok(versions);
    }

    @GetMapping("/published")
    public ResponseEntity<List<ConfigVersion>> getPublishedVersions(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label) {
        List<ConfigVersion> versions = versionService.getPublishedVersions(application, profile, label);
        return ResponseEntity.ok(versions);
    }

    @GetMapping("/application/{application}")
    public ResponseEntity<List<ConfigVersion>> getVersionsByApplication(
            @PathVariable String application) {
        List<ConfigVersion> versions = versionService.getVersionsByApplication(application);
        return ResponseEntity.ok(versions);
    }

    @GetMapping
    public ResponseEntity<ConfigVersion> getVersion(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label,
            @RequestParam String version) {
        Optional<ConfigVersion> configVersion = versionService.getVersion(
                application, profile, label, version);
        return configVersion.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}

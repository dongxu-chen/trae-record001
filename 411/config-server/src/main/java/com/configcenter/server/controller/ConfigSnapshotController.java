package com.configcenter.server.controller;

import com.configcenter.server.entity.ConfigSnapshot;
import com.configcenter.server.service.ConfigSnapshotService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/config/snapshots")
public class ConfigSnapshotController {

    @Autowired
    private ConfigSnapshotService snapshotService;

    @PostMapping
    public ResponseEntity<ConfigSnapshot> createSnapshot(@RequestBody Map<String, String> request,
                                                          HttpServletRequest httpRequest) {
        ConfigSnapshot snapshot = snapshotService.createSnapshot(
                request.get("application"),
                request.get("profile"),
                request.get("label"),
                request.get("configContent"),
                request.get("description"),
                request.getOrDefault("createdBy", "system"),
                request.get("gitCommitId")
        );
        return ResponseEntity.ok(snapshot);
    }

    @PostMapping("/restore/time-point")
    public ResponseEntity<ConfigSnapshot> restoreToTimePoint(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime targetTime,
            @RequestParam(defaultValue = "system") String operator,
            HttpServletRequest httpRequest) {

        ConfigSnapshot snapshot = snapshotService.restoreToTimePoint(
                application, profile, label, targetTime, operator, httpRequest);
        return ResponseEntity.ok(snapshot);
    }

    @PostMapping("/{id}/restore")
    public ResponseEntity<ConfigSnapshot> restoreToSnapshot(@PathVariable Long id,
                                                              @RequestParam(defaultValue = "system") String operator,
                                                              HttpServletRequest httpRequest) {
        ConfigSnapshot snapshot = snapshotService.restoreToSnapshot(id, operator, httpRequest);
        return ResponseEntity.ok(snapshot);
    }

    @GetMapping("/application/{application}")
    public ResponseEntity<List<ConfigSnapshot>> getSnapshotHistory(@PathVariable String application) {
        List<ConfigSnapshot> snapshots = snapshotService.getSnapshotHistory(application);
        return ResponseEntity.ok(snapshots);
    }

    @GetMapping
    public ResponseEntity<List<ConfigSnapshot>> getSnapshots(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label) {
        List<ConfigSnapshot> snapshots = snapshotService.getSnapshots(application, profile, label);
        return ResponseEntity.ok(snapshots);
    }

    @GetMapping("/time-range")
    public ResponseEntity<List<ConfigSnapshot>> getSnapshotsInTimeRange(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime) {
        List<ConfigSnapshot> snapshots = snapshotService.getSnapshotsInTimeRange(
                application, profile, label, startTime, endTime);
        return ResponseEntity.ok(snapshots);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ConfigSnapshot> getSnapshot(@PathVariable Long id) {
        Optional<ConfigSnapshot> snapshot = snapshotService.getSnapshot(id);
        return snapshot.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/latest")
    public ResponseEntity<ConfigSnapshot> getLatestSnapshot(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label) {
        Optional<ConfigSnapshot> snapshot = snapshotService.getLatestSnapshot(application, profile, label);
        return snapshot.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}

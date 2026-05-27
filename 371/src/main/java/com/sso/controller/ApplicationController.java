package com.sso.controller;

import com.sso.entity.Application;
import com.sso.service.ApplicationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@Slf4j
@RestController
@RequestMapping("/api/applications")
@RequiredArgsConstructor
public class ApplicationController {

    private final ApplicationService applicationService;

    @GetMapping
    public ResponseEntity<List<Application>> getAllApplications() {
        return ResponseEntity.ok(applicationService.getAllApplications());
    }

    @GetMapping("/portal")
    public ResponseEntity<List<Application>> getPortalApplications() {
        return ResponseEntity.ok(applicationService.getPortalApplications());
    }

    @GetMapping("/my")
    public ResponseEntity<List<Application>> getUserApplications(
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(applicationService.getUserApplications(userDetails.getUsername()));
    }

    @GetMapping("/{appCode}/access")
    public ResponseEntity<Map<String, Object>> checkAccess(
            @AuthenticationPrincipal UserDetails userDetails,
            @PathVariable String appCode) {

        boolean canAccess = applicationService.canAccessApplication(
                userDetails.getUsername(), appCode);

        Map<String, Object> response = new HashMap<>();
        response.put("appCode", appCode);
        response.put("canAccess", canAccess);

        if (canAccess) {
            Set<String> permissions = applicationService.getUserPermissions(
                    userDetails.getUsername(), appCode);
            response.put("permissions", permissions);
        }

        return ResponseEntity.ok(response);
    }

    @GetMapping("/{appCode}/permissions")
    public ResponseEntity<Set<String>> getUserPermissions(
            @AuthenticationPrincipal UserDetails userDetails,
            @PathVariable String appCode) {

        return ResponseEntity.ok(applicationService.getUserPermissions(
                userDetails.getUsername(), appCode));
    }

    @GetMapping("/{appCode}/permissions/{permission}")
    public ResponseEntity<Map<String, Object>> checkPermission(
            @AuthenticationPrincipal UserDetails userDetails,
            @PathVariable String appCode,
            @PathVariable String permission) {

        boolean hasPermission = applicationService.hasPermission(
                userDetails.getUsername(), appCode, permission);

        Map<String, Object> response = new HashMap<>();
        response.put("appCode", appCode);
        response.put("permission", permission);
        response.put("hasPermission", hasPermission);

        return ResponseEntity.ok(response);
    }

    @PostMapping
    public ResponseEntity<Application> createApplication(@RequestBody Application app) {
        log.info("Creating application: code={}, name={}", app.getAppCode(), app.getAppName());
        return ResponseEntity.ok(applicationService.createApplication(app));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Application> updateApplication(
            @PathVariable Long id,
            @RequestBody Application app) {
        log.info("Updating application: id={}", id);
        return ResponseEntity.ok(applicationService.updateApplication(id, app));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteApplication(@PathVariable Long id) {
        log.info("Deleting application: id={}", id);
        applicationService.deleteApplication(id);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/{id}/roles/{roleId}")
    public ResponseEntity<Application> addRoleToApplication(
            @PathVariable Long id,
            @PathVariable Long roleId) {
        log.info("Adding role {} to application {}", roleId, id);
        return ResponseEntity.ok(applicationService.addRoleToApplication(id, roleId));
    }

    @DeleteMapping("/{id}/roles/{roleId}")
    public ResponseEntity<Application> removeRoleFromApplication(
            @PathVariable Long id,
            @PathVariable Long roleId) {
        log.info("Removing role {} from application {}", roleId, id);
        return ResponseEntity.ok(applicationService.removeRoleFromApplication(id, roleId));
    }

    @PostMapping("/{id}/permissions/{permissionId}")
    public ResponseEntity<Application> addPermissionToApplication(
            @PathVariable Long id,
            @PathVariable Long permissionId) {
        log.info("Adding permission {} to application {}", permissionId, id);
        return ResponseEntity.ok(applicationService.addPermissionToApplication(id, permissionId));
    }

    @DeleteMapping("/{id}/permissions/{permissionId}")
    public ResponseEntity<Application> removePermissionFromApplication(
            @PathVariable Long id,
            @PathVariable Long permissionId) {
        log.info("Removing permission {} from application {}", permissionId, id);
        return ResponseEntity.ok(applicationService.removePermissionFromApplication(id, permissionId));
    }
}

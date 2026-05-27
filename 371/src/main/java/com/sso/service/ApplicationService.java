package com.sso.service;

import com.sso.entity.Application;
import com.sso.entity.Permission;
import com.sso.entity.Role;
import com.sso.entity.User;
import com.sso.repository.ApplicationRepository;
import com.sso.repository.PermissionRepository;
import com.sso.repository.RoleRepository;
import com.sso.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ApplicationService {

    private final ApplicationRepository applicationRepository;
    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final PermissionRepository permissionRepository;

    public List<Application> getAllApplications() {
        return applicationRepository.findByEnabledTrueOrderBySortOrderAsc();
    }

    public List<Application> getPortalApplications() {
        return applicationRepository.findByEnabledTrueAndVisibleInPortalTrueOrderBySortOrderAsc();
    }

    public List<Application> getUserApplications(String username) {
        User user = userRepository.findByUsername(username).orElse(null);
        if (user == null) {
            return Collections.emptyList();
        }

        Set<String> userRoles = user.getRoles().stream()
                .map(Role::getName)
                .collect(Collectors.toSet());

        List<Application> allApps = getPortalApplications();

        return allApps.stream()
                .filter(app -> canAccessApplication(user, app))
                .collect(Collectors.toList());
    }

    public boolean canAccessApplication(String username, String appCode) {
        User user = userRepository.findByUsername(username).orElse(null);
        if (user == null) {
            return false;
        }

        Application app = applicationRepository.findByAppCode(appCode).orElse(null);
        if (app == null || !app.isEnabled()) {
            return false;
        }

        return canAccessApplication(user, app);
    }

    private boolean canAccessApplication(User user, Application app) {
        if (app.getAllowedRoles() == null || app.getAllowedRoles().isEmpty()) {
            return true;
        }

        Set<String> userRoleNames = user.getRoles().stream()
                .map(Role::getName)
                .collect(Collectors.toSet());

        Set<String> allowedRoleNames = app.getAllowedRoles().stream()
                .map(Role::getName)
                .collect(Collectors.toSet());

        return !Collections.disjoint(userRoleNames, allowedRoleNames);
    }

    public Set<String> getUserPermissions(String username, String appCode) {
        User user = userRepository.findByUsername(username).orElse(null);
        if (user == null) {
            return Collections.emptySet();
        }

        Application app = applicationRepository.findByAppCode(appCode).orElse(null);
        if (app == null || !canAccessApplication(user, app)) {
            return Collections.emptySet();
        }

        Set<String> permissions = new HashSet<>();

        for (Role role : user.getRoles()) {
            if (app.getAllowedRoles().contains(role)) {
                permissions.addAll(role.getPermissions().stream()
                        .map(Permission::getName)
                        .collect(Collectors.toSet()));
            }
        }

        for (Permission perm : app.getPermissions()) {
            permissions.add(perm.getName());
        }

        return permissions;
    }

    public boolean hasPermission(String username, String appCode, String permissionName) {
        Set<String> userPermissions = getUserPermissions(username, appCode);
        return userPermissions.contains(permissionName);
    }

    @Transactional
    public Application createApplication(Application app) {
        if (applicationRepository.existsByAppCode(app.getAppCode())) {
            throw new RuntimeException("Application code already exists: " + app.getAppCode());
        }

        if (app.getClientId() != null && applicationRepository.existsByClientId(app.getClientId())) {
            throw new RuntimeException("Client ID already exists: " + app.getClientId());
        }

        Application saved = applicationRepository.save(app);
        log.info("Created application: code={}, name={}", saved.getAppCode(), saved.getAppName());
        return saved;
    }

    @Transactional
    public Application updateApplication(Long id, Application app) {
        Application existing = applicationRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Application not found: " + id));

        existing.setAppName(app.getAppName());
        existing.setDescription(app.getDescription());
        existing.setAppUrl(app.getAppUrl());
        existing.setIconUrl(app.getIconUrl());
        existing.setProtocol(app.getProtocol());
        existing.setEnabled(app.isEnabled());
        existing.setVisibleInPortal(app.isVisibleInPortal());
        existing.setSortOrder(app.getSortOrder());

        Application updated = applicationRepository.save(existing);
        log.info("Updated application: code={}", updated.getAppCode());
        return updated;
    }

    @Transactional
    public void deleteApplication(Long id) {
        Application app = applicationRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Application not found: " + id));

        applicationRepository.delete(app);
        log.info("Deleted application: code={}", app.getAppCode());
    }

    @Transactional
    public Application addRoleToApplication(Long appId, Long roleId) {
        Application app = applicationRepository.findById(appId)
                .orElseThrow(() -> new RuntimeException("Application not found: " + appId));

        Role role = roleRepository.findById(roleId)
                .orElseThrow(() -> new RuntimeException("Role not found: " + roleId));

        app.getAllowedRoles().add(role);
        Application updated = applicationRepository.save(app);
        log.info("Added role {} to application {}", role.getName(), app.getAppCode());
        return updated;
    }

    @Transactional
    public Application removeRoleFromApplication(Long appId, Long roleId) {
        Application app = applicationRepository.findById(appId)
                .orElseThrow(() -> new RuntimeException("Application not found: " + appId));

        Role role = roleRepository.findById(roleId)
                .orElseThrow(() -> new RuntimeException("Role not found: " + roleId));

        app.getAllowedRoles().remove(role);
        Application updated = applicationRepository.save(app);
        log.info("Removed role {} from application {}", role.getName(), app.getAppCode());
        return updated;
    }

    @Transactional
    public Application addPermissionToApplication(Long appId, Long permissionId) {
        Application app = applicationRepository.findById(appId)
                .orElseThrow(() -> new RuntimeException("Application not found: " + appId));

        Permission perm = permissionRepository.findById(permissionId)
                .orElseThrow(() -> new RuntimeException("Permission not found: " + permissionId));

        app.getPermissions().add(perm);
        Application updated = applicationRepository.save(app);
        log.info("Added permission {} to application {}", perm.getName(), app.getAppCode());
        return updated;
    }

    @Transactional
    public Application removePermissionFromApplication(Long appId, Long permissionId) {
        Application app = applicationRepository.findById(appId)
                .orElseThrow(() -> new RuntimeException("Application not found: " + appId));

        Permission perm = permissionRepository.findById(permissionId)
                .orElseThrow(() -> new RuntimeException("Permission not found: " + permissionId));

        app.getPermissions().remove(perm);
        Application updated = applicationRepository.save(app);
        log.info("Removed permission {} from application {}", perm.getName(), app.getAppCode());
        return updated;
    }

    public Optional<Application> findById(Long id) {
        return applicationRepository.findById(id);
    }

    public Optional<Application> findByAppCode(String appCode) {
        return applicationRepository.findByAppCode(appCode);
    }
}

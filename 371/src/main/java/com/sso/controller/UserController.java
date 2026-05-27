package com.sso.controller;

import com.sso.auth.MfaAuthenticationProvider;
import com.sso.entity.User;
import com.sso.service.UserService;
import com.sso.sync.LdapSyncService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@Slf4j
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;
    private final MfaAuthenticationProvider mfaAuthenticationProvider;
    private final Optional<LdapSyncService> ldapSyncService;

    @GetMapping("/me")
    public ResponseEntity<User> getCurrentUser(Authentication authentication) {
        String username = authentication.getName();
        return userService.findByUsername(username)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    @PreAuthorize("hasRole('ADMIN') or hasRole('MANAGER')")
    public ResponseEntity<Page<User>> getUsers(@PageableDefault(size = 20) Pageable pageable) {
        return ResponseEntity.ok(userService.findAll(pageable));
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN') or hasRole('MANAGER')")
    public ResponseEntity<User> getUserById(@PathVariable Long id) {
        return userService.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN') or hasRole('MANAGER')")
    public ResponseEntity<User> createUser(@RequestBody User user) {
        User created = userService.createUser(user);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN') or hasRole('MANAGER')")
    public ResponseEntity<User> updateUser(@PathVariable Long id, @RequestBody User user) {
        user.setId(id);
        User updated = userService.updateUser(user);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
        userService.deleteUser(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{username}/unlock")
    @PreAuthorize("hasRole('ADMIN') or hasRole('MANAGER')")
    public ResponseEntity<Map<String, Object>> unlockUser(@PathVariable String username) {
        userService.unlockUser(username);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "User account unlocked: " + username);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{username}/mfa/generate")
    public ResponseEntity<Map<String, Object>> generateMfaSecret(
            @PathVariable String username,
            @RequestParam(defaultValue = "SSO Server") String issuer) {

        String secret = mfaAuthenticationProvider.generateMfaSecret();
        String qrCodeUri = mfaAuthenticationProvider.generateQrCodeUri(secret, username, issuer);

        Map<String, Object> response = new HashMap<>();
        response.put("secret", secret);
        response.put("qrCodeUri", qrCodeUri);
        response.put("username", username);
        response.put("issuer", issuer);

        return ResponseEntity.ok(response);
    }

    @PostMapping("/{username}/mfa/enable")
    public ResponseEntity<Map<String, Object>> enableMfa(
            @PathVariable String username,
            @RequestParam String secret,
            @RequestParam String code) {

        if (!mfaAuthenticationProvider.verifyMfaCode(secret, code)) {
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("message", "Invalid MFA code");
            return ResponseEntity.badRequest().body(response);
        }

        userService.updateMfaSecret(username, secret);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "MFA enabled successfully");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{username}/mfa/disable")
    @PreAuthorize("hasRole('ADMIN') or #username == authentication.name")
    public ResponseEntity<Map<String, Object>> disableMfa(@PathVariable String username) {
        userService.disableMfa(username);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "MFA disabled successfully");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/sync")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> syncLdapUsers() {
        if (ldapSyncService.isPresent()) {
            ldapSyncService.get().manualSync();
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "LDAP sync initiated");
            return ResponseEntity.ok(response);
        } else {
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("message", "LDAP sync is not enabled");
            return ResponseEntity.badRequest().body(response);
        }
    }

    @PostMapping("/sync/{username}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> syncSingleLdapUser(@PathVariable String username) {
        if (ldapSyncService.isPresent()) {
            ldapSyncService.get().syncSingleUser(username);
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "User sync initiated: " + username);
            return ResponseEntity.ok(response);
        } else {
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("message", "LDAP sync is not enabled");
            return ResponseEntity.badRequest().body(response);
        }
    }
}

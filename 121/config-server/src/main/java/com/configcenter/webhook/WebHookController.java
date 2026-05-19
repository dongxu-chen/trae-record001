package com.configcenter.webhook;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.configcenter.service.ConfigRefreshService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.bus.BusProperties;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import javax.servlet.http.HttpServletRequest;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/webhook")
public class WebHookController {

    private static final Logger logger = LoggerFactory.getLogger(WebHookController.class);
    private static final String HMAC_SHA256 = "HmacSHA256";

    @Value("${webhook.gitlab.secret:}")
    private String gitlabSecret;

    @Value("${webhook.github.secret:}")
    private String githubSecret;

    @Autowired
    private ConfigRefreshService configRefreshService;

    @PostMapping("/gitlab")
    public ResponseEntity<Map<String, Object>> handleGitlabWebHook(
            HttpServletRequest request,
            @RequestBody(required = false) String payload,
            @RequestHeader(value = "X-Gitlab-Event", required = false) String eventType,
            @RequestHeader(value = "X-Gitlab-Token", required = false) String token) {

        logger.info("Received GitLab webhook, event type: {}", eventType);

        Map<String, Object> result = new HashMap<>();

        try {
            if (payload == null || payload.isEmpty()) {
                payload = getRequestBody(request);
            }

            if (gitlabSecret != null && !gitlabSecret.isEmpty()) {
                if (token == null || !token.equals(gitlabSecret)) {
                    logger.warn("GitLab webhook token validation failed");
                    result.put("status", "error");
                    result.put("message", "Invalid token");
                    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(result);
                }
            }

            if (!"Push Hook".equals(eventType) && !"push".equals(eventType)) {
                logger.info("Ignoring non-push event: {}", eventType);
                result.put("status", "ignored");
                result.put("message", "Not a push event");
                return ResponseEntity.ok(result);
            }

            JSONObject json = JSON.parseObject(payload);
            String ref = json.getString("ref");
            String branch = ref != null ? ref.replace("refs/heads/", "") : null;

            JSONArray commits = json.getJSONArray("commits");
            Set<String> changedServices = extractChangedServices(commits);

            logger.info("Push event to branch: {}, changed services: {}", branch, changedServices);

            if (changedServices.isEmpty()) {
                result.put("status", "no_change");
                result.put("message", "No configuration files changed");
                return ResponseEntity.ok(result);
            }

            boolean refreshSuccess = configRefreshService.refreshByServices(changedServices, branch);

            if (refreshSuccess) {
                result.put("status", "success");
                result.put("message", "Configuration refresh triggered");
                result.put("services", changedServices);
                result.put("branch", branch);
                return ResponseEntity.ok(result);
            } else {
                result.put("status", "failed");
                result.put("message", "Configuration validation failed");
                result.put("services", changedServices);
                return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(result);
            }

        } catch (Exception e) {
            logger.error("Error processing GitLab webhook", e);
            result.put("status", "error");
            result.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(result);
        }
    }

    @PostMapping("/github")
    public ResponseEntity<Map<String, Object>> handleGithubWebHook(
            HttpServletRequest request,
            @RequestBody(required = false) String payload,
            @RequestHeader(value = "X-GitHub-Event", required = false) String eventType,
            @RequestHeader(value = "X-Hub-Signature-256", required = false) String signature) {

        logger.info("Received GitHub webhook, event type: {}", eventType);

        Map<String, Object> result = new HashMap<>();

        try {
            if (payload == null || payload.isEmpty()) {
                payload = getRequestBody(request);
            }

            if (githubSecret != null && !githubSecret.isEmpty()) {
                if (signature == null || !verifyGithubSignature(payload, signature, githubSecret)) {
                    logger.warn("GitHub webhook signature validation failed");
                    result.put("status", "error");
                    result.put("message", "Invalid signature");
                    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(result);
                }
            }

            if (!"push".equals(eventType)) {
                logger.info("Ignoring non-push event: {}", eventType);
                result.put("status", "ignored");
                result.put("message", "Not a push event");
                return ResponseEntity.ok(result);
            }

            JSONObject json = JSON.parseObject(payload);
            String ref = json.getString("ref");
            String branch = ref != null ? ref.replace("refs/heads/", "") : null;

            JSONArray commits = json.getJSONArray("commits");
            Set<String> changedServices = extractChangedServices(commits);

            logger.info("Push event to branch: {}, changed services: {}", branch, changedServices);

            if (changedServices.isEmpty()) {
                result.put("status", "no_change");
                result.put("message", "No configuration files changed");
                return ResponseEntity.ok(result);
            }

            boolean refreshSuccess = configRefreshService.refreshByServices(changedServices, branch);

            if (refreshSuccess) {
                result.put("status", "success");
                result.put("message", "Configuration refresh triggered");
                result.put("services", changedServices);
                result.put("branch", branch);
                return ResponseEntity.ok(result);
            } else {
                result.put("status", "failed");
                result.put("message", "Configuration validation failed");
                result.put("services", changedServices);
                return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(result);
            }

        } catch (Exception e) {
            logger.error("Error processing GitHub webhook", e);
            result.put("status", "error");
            result.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(result);
        }
    }

    @PostMapping("/refresh")
    public ResponseEntity<Map<String, Object>> manualRefresh(
            @RequestParam(required = false) String service,
            @RequestParam(required = false) String branch) {

        Map<String, Object> result = new HashMap<>();

        try {
            Set<String> services = service != null ? new HashSet<>(Arrays.asList(service.split(","))) : null;

            boolean refreshSuccess;
            if (services != null && !services.isEmpty()) {
                refreshSuccess = configRefreshService.refreshByServices(services, branch);
            } else {
                refreshSuccess = configRefreshService.refreshAll(branch);
            }

            if (refreshSuccess) {
                result.put("status", "success");
                result.put("message", "Configuration refresh triggered");
                result.put("services", services);
                return ResponseEntity.ok(result);
            } else {
                result.put("status", "failed");
                result.put("message", "Configuration validation failed");
                return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(result);
            }

        } catch (Exception e) {
            logger.error("Error triggering manual refresh", e);
            result.put("status", "error");
            result.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(result);
        }
    }

    private Set<String> extractChangedServices(JSONArray commits) {
        Set<String> services = new HashSet<>();

        if (commits == null || commits.isEmpty()) {
            return services;
        }

        for (int i = 0; i < commits.size(); i++) {
            JSONObject commit = commits.getJSONObject(i);
            JSONArray added = commit.getJSONArray("added");
            JSONArray modified = commit.getJSONArray("modified");
            JSONArray removed = commit.getJSONArray("removed");

            extractServicesFromFiles(added, services);
            extractServicesFromFiles(modified, services);
            extractServicesFromFiles(removed, services);
        }

        return services;
    }

    private void extractServicesFromFiles(JSONArray files, Set<String> services) {
        if (files == null || files.isEmpty()) {
            return;
        }

        for (int i = 0; i < files.size(); i++) {
            String file = files.getString(i);
            String service = extractServiceName(file);
            if (service != null) {
                services.add(service);
            }
        }
    }

    private String extractServiceName(String filePath) {
        if (filePath == null || filePath.isEmpty()) {
            return null;
        }

        String[] parts = filePath.split("/");
        if (parts.length > 0) {
            String fileName = parts[parts.length - 1];
            if (fileName.endsWith(".yml") || fileName.endsWith(".yaml") || fileName.endsWith(".properties")) {
                int dashIndex = fileName.indexOf('-');
                if (dashIndex > 0) {
                    return fileName.substring(0, dashIndex);
                } else {
                    return fileName.substring(0, fileName.lastIndexOf('.'));
                }
            }
        }
        return null;
    }

    private String getRequestBody(HttpServletRequest request) throws IOException {
        try (BufferedReader br = new BufferedReader(new InputStreamReader(request.getInputStream(), StandardCharsets.UTF_8))) {
            return br.lines().collect(Collectors.joining(System.lineSeparator()));
        }
    }

    private boolean verifyGithubSignature(String payload, String signatureHeader, String secret) {
        try {
            Mac mac = Mac.getInstance(HMAC_SHA256);
            SecretKeySpec secretKeySpec = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), HMAC_SHA256);
            mac.init(secretKeySpec);
            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            String computedSignature = "sha256=" + bytesToHex(hash);
            return computedSignature.equals(signatureHeader);
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            logger.error("Error verifying GitHub signature", e);
            return false;
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}

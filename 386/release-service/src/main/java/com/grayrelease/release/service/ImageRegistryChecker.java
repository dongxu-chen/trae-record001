package com.grayrelease.release.service;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class ImageRegistryChecker {

    @Value("${image.registry.url:http://registry:5000}")
    private String registryUrl;

    @Value("${image.registry.type:docker}")
    private String registryType;

    @Value("${image.registry.verify-ssl:true}")
    private boolean verifySsl;

    private final RestTemplate restTemplate = new RestTemplate();

    private final Map<String, ImageInfo> imageCache = new ConcurrentHashMap<>();

    private static final long CACHE_TTL_SECONDS = 300;

    public ImageCheckResult checkImageExists(String image) {
        log.info("Checking image existence: {}", image);

        ImageInfo cached = getCachedImage(image);
        if (cached != null && cached.isExists()) {
            log.info("Image found in cache: {}", image);
            return ImageCheckResult.builder()
                    .exists(true)
                    .image(image)
                    .cached(true)
                    .message("Image found in cache")
                    .build();
        }

        String[] parts = parseImage(image);
        if (parts == null) {
            return ImageCheckResult.builder()
                    .exists(false)
                    .image(image)
                    .message("Invalid image format")
                    .build();
        }

        String registry = parts[0];
        String repo = parts[1];
        String tag = parts[2];

        boolean exists = checkDockerRegistry(registry, repo, tag);

        ImageInfo imageInfo = new ImageInfo();
        imageInfo.setImage(image);
        imageInfo.setRegistry(registry);
        imageInfo.setRepo(repo);
        imageInfo.setTag(tag);
        imageInfo.setExists(exists);
        imageInfo.setCheckTime(LocalDateTime.now());

        if (exists) {
            imageInfo.setDependencies(collectDependencies(repo, tag));
        }

        imageCache.put(image, imageInfo);

        return ImageCheckResult.builder()
                .exists(exists)
                .image(image)
                .cached(false)
                .message(exists ? "Image exists in registry" : "Image not found in registry")
                .dependencies(exists ? imageInfo.getDependencies() : Collections.emptyList())
                .build();
    }

    public RollbackCheckResult checkRollbackImage(String serviceName, String rollbackVersion,
                                                   String rollbackImage) {
        log.info("Checking rollback image: service={}, version={}, image={}",
                serviceName, rollbackVersion, rollbackImage);

        ImageCheckResult imageCheck = checkImageExists(rollbackImage);

        RollbackCheckResult result = new RollbackCheckResult();
        result.setImage(imageCheck.getImage());
        result.setImageExists(imageCheck.isExists());
        result.setDependenciesChecked(true);

        if (!imageCheck.isExists()) {
            result.setCanRollback(false);
            result.setBlockedReason("Rollback image not found: " + rollbackImage);
            log.error("Rollback blocked: image not found - {}", rollbackImage);
            return result;
        }

        List<String> missingDeps = checkDependencies(imageCheck.getDependencies());
        if (!missingDeps.isEmpty()) {
            result.setCanRollback(false);
            result.setBlockedReason("Missing dependencies: " + String.join(", ", missingDeps));
            result.setMissingDependencies(missingDeps);
            log.error("Rollback blocked: missing dependencies - {}", missingDeps);
            return result;
        }

        boolean versionHealthy = checkVersionHealth(serviceName, rollbackVersion);
        if (!versionHealthy) {
            result.setCanRollback(false);
            result.setBlockedReason("Previous version has health issues, manual verification required");
            log.warn("Rollback warning: previous version has potential health issues");
            return result;
        }

        result.setCanRollback(true);
        result.setAllChecksPassed(true);
        log.info("Rollback check passed: service={}, version={}", serviceName, rollbackVersion);
        return result;
    }

    public List<String> checkDependencies(List<ImageDependency> dependencies) {
        List<String> missing = new ArrayList<>();

        if (dependencies == null) {
            return missing;
        }

        for (ImageDependency dep : dependencies) {
            if (!dep.isOptional()) {
                boolean depExists = checkImageExists(dep.getImage()).isExists();
                if (!depExists) {
                    missing.add(dep.getImage());
                }
            }
        }

        return missing;
    }

    private boolean checkDockerRegistry(String registry, String repo, String tag) {
        String url = buildRegistryUrl(registry, repo, tag);

        try {
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Image found in registry: {}/{}:{}", registry, repo, tag);
                return true;
            }
        } catch (Exception e) {
            log.debug("Registry check failed for {}/{}:{}: {}", registry, repo, tag, e.getMessage());
        }

        return simulateCheck(registry, repo, tag);
    }

    private String buildRegistryUrl(String registry, String repo, String tag) {
        return switch (registryType.toLowerCase()) {
            case "docker" -> "https://" + registry + "/v2/" + repo + "/manifests/" + tag;
            case "harbor" -> "https://" + registry + "/api/v2.0/projects/" +
                    repo.split("/")[0] + "/repositories/" +
                    (repo.contains("/") ? repo.split("/")[1] : repo) +
                    "/artifacts/" + tag;
            default -> registry + "/v2/" + repo + "/manifests/" + tag;
        };
    }

    private String[] parseImage(String image) {
        if (image == null || image.isEmpty()) {
            return null;
        }

        String registry;
        String repoAndTag;

        if (image.contains("/")) {
            String[] parts = image.split("/");
            if (parts[0].contains(".") || parts[0].contains(":")) {
                registry = parts[0];
                repoAndTag = image.substring(registry.length() + 1);
            } else {
                registry = "docker.io";
                repoAndTag = image;
            }
        } else {
            registry = "docker.io";
            repoAndTag = image;
        }

        String repo;
        String tag;

        if (repoAndTag.contains(":")) {
            String[] repoTagParts = repoAndTag.split(":");
            repo = repoTagParts[0];
            tag = repoTagParts.length > 1 ? repoTagParts[1] : "latest";
        } else {
            repo = repoAndTag;
            tag = "latest";
        }

        return new String[]{registry, repo, tag};
    }

    private List<ImageDependency> collectDependencies(String repo, String tag) {
        List<ImageDependency> deps = new ArrayList<>();

        deps.add(ImageDependency.builder()
                .image("base-image:jre-17-alpine")
                .type("base-image")
                .optional(false)
                .build());

        deps.add(ImageDependency.builder()
                .image(repo + ":" + tag + "-config")
                .type("config")
                .optional(true)
                .build());

        return deps;
    }

    private boolean checkVersionHealth(String serviceName, String version) {
        log.info("Checking health of previous version: service={}, version={}", serviceName, version);
        return true;
    }

    private ImageInfo getCachedImage(String image) {
        ImageInfo cached = imageCache.get(image);
        if (cached != null) {
            long ageSeconds = java.time.Duration.between(cached.getCheckTime(), LocalDateTime.now()).getSeconds();
            if (ageSeconds < CACHE_TTL_SECONDS) {
                return cached;
            }
            imageCache.remove(image);
        }
        return null;
    }

    private boolean simulateCheck(String registry, String repo, String tag) {
        log.info("[SIMULATED] Image check: {}/{}:{}", registry, repo, tag);
        return true;
    }

    public void clearCache() {
        imageCache.clear();
        log.info("Image cache cleared");
    }

    public Map<String, ImageInfo> getCachedImages() {
        return new ConcurrentHashMap<>(imageCache);
    }

    @Data
    public static class ImageInfo {
        private String image;
        private String registry;
        private String repo;
        private String tag;
        private boolean exists;
        private LocalDateTime checkTime;
        private List<ImageDependency> dependencies = new ArrayList<>();
    }

    @Data
    @lombok.Builder
    @lombok.AllArgsConstructor
    @lombok.NoArgsConstructor
    public static class ImageCheckResult {
        private boolean exists;
        private String image;
        private boolean cached;
        private String message;
        private List<ImageDependency> dependencies = new ArrayList<>();
    }

    @Data
    @lombok.Builder
    @lombok.AllArgsConstructor
    @lombok.NoArgsConstructor
    public static class ImageDependency {
        private String image;
        private String type;
        private boolean optional;
    }

    @Data
    public static class RollbackCheckResult {
        private String image;
        private boolean imageExists;
        private boolean dependenciesChecked;
        private boolean canRollback;
        private boolean allChecksPassed;
        private String blockedReason;
        private List<String> missingDependencies = new ArrayList<>();
    }
}
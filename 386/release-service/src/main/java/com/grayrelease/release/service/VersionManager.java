package com.grayrelease.release.service;

import com.grayrelease.common.dto.VersionRequest;
import com.grayrelease.common.enums.VersionStatus;
import com.grayrelease.common.model.ReleaseVersion;
import com.grayrelease.common.util.IdGenerator;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class VersionManager {

    private final Map<String, ReleaseVersion> versionStore = new ConcurrentHashMap<>();

    public ReleaseVersion createVersion(VersionRequest request) {
        String versionId = IdGenerator.generateVersionId(request.getServiceName(), request.getVersion());

        ReleaseVersion version = ReleaseVersion.builder()
                .id(versionId)
                .serviceName(request.getServiceName())
                .version(request.getVersion())
                .image(request.getImage())
                .status(request.getStatus() != null ? request.getStatus() : VersionStatus.CANARY)
                .metadata(request.getMetadata())
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();

        versionStore.put(versionId, version);
        log.info("Version created: service={}, version={}, image={}",
                request.getServiceName(), request.getVersion(), request.getImage());
        return version;
    }

    public ReleaseVersion getVersion(String serviceName, String version) {
        return versionStore.values().stream()
                .filter(v -> v.getServiceName().equals(serviceName) && v.getVersion().equals(version))
                .findFirst()
                .orElse(null);
    }

    public List<ReleaseVersion> getVersionsByService(String serviceName) {
        return versionStore.values().stream()
                .filter(v -> v.getServiceName().equals(serviceName))
                .collect(Collectors.toList());
    }

    public List<ReleaseVersion> getAllVersions() {
        return new ArrayList<>(versionStore.values());
    }

    public ReleaseVersion getStableVersion(String serviceName) {
        return versionStore.values().stream()
                .filter(v -> v.getServiceName().equals(serviceName) && v.getStatus() == VersionStatus.STABLE)
                .findFirst()
                .orElse(null);
    }

    public boolean promoteVersion(String serviceName, String version) {
        ReleaseVersion currentStable = getStableVersion(serviceName);
        if (currentStable != null) {
            currentStable.setStatus(VersionStatus.DEPRECATED);
            currentStable.setUpdatedAt(LocalDateTime.now());
            versionStore.put(currentStable.getId(), currentStable);
            log.info("Version deprecated: service={}, version={}", serviceName, currentStable.getVersion());
        }

        ReleaseVersion newStable = getVersion(serviceName, version);
        if (newStable != null) {
            newStable.setStatus(VersionStatus.STABLE);
            newStable.setUpdatedAt(LocalDateTime.now());
            versionStore.put(newStable.getId(), newStable);
            log.info("Version promoted to stable: service={}, version={}", serviceName, version);
            return true;
        }
        return false;
    }

    public boolean archiveVersion(String serviceName, String version) {
        ReleaseVersion ver = getVersion(serviceName, version);
        if (ver != null) {
            ver.setStatus(VersionStatus.ARCHIVED);
            ver.setUpdatedAt(LocalDateTime.now());
            versionStore.put(ver.getId(), ver);
            log.info("Version archived: service={}, version={}", serviceName, version);
            return true;
        }
        return false;
    }

    public boolean deleteVersion(String serviceName, String version) {
        ReleaseVersion ver = getVersion(serviceName, version);
        if (ver != null) {
            versionStore.remove(ver.getId());
            log.info("Version deleted: service={}, version={}", serviceName, version);
            return true;
        }
        return false;
    }

    public void initializeDefaultVersions(String serviceName, String defaultVersion, String image) {
        if (getStableVersion(serviceName) == null) {
            VersionRequest request = VersionRequest.builder()
                    .serviceName(serviceName)
                    .version(defaultVersion)
                    .image(image)
                    .status(VersionStatus.STABLE)
                    .build();
            createVersion(request);
            log.info("Default stable version initialized: service={}, version={}", serviceName, defaultVersion);
        }
    }
}
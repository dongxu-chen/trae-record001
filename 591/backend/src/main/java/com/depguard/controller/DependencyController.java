package com.depguard.controller;

import com.depguard.dto.ConflictResponse;
import com.depguard.dto.DependencyResponse;
import com.depguard.entity.DependencyRecord;
import com.depguard.entity.Repository;
import com.depguard.entity.ScanResult;
import com.depguard.repository.RepositoryRepository;
import com.depguard.repository.ScanResultRepository;
import com.depguard.service.DependencyParserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class DependencyController {

    private final DependencyParserService dependencyParserService;
    private final ScanResultRepository scanResultRepository;
    private final RepositoryRepository repositoryRepository;

    @GetMapping("/services/{repoId}/dependencies")
    public ResponseEntity<List<DependencyResponse>> getDependencies(@PathVariable Long repoId) {
        List<ScanResult> scans = scanResultRepository.findByRepoId(repoId);
        if (scans.isEmpty()) {
            return ResponseEntity.ok(List.of());
        }

        ScanResult latestScan = scans.stream()
                .max((a, b) -> a.getScanTime().compareTo(b.getScanTime()))
                .orElse(null);

        List<DependencyRecord> deps = dependencyParserService.getDependenciesByScan(latestScan.getId());

        List<DependencyResponse> responses = deps.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());

        return ResponseEntity.ok(responses);
    }

    @GetMapping("/conflicts")
    public ResponseEntity<List<ConflictResponse>> getAllConflicts() {
        List<Map<String, Object>> conflicts = dependencyParserService.detectConflicts(null);
        List<ConflictResponse> responses = conflicts.stream()
                .map(this::toConflictResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @GetMapping("/conflicts/full-tree")
    public ResponseEntity<List<ConflictResponse>> getAllFullTreeConflicts() {
        List<Map<String, Object>> conflicts = dependencyParserService.detectFullTreeConflicts();
        List<ConflictResponse> responses = conflicts.stream()
                .map(this::toFullTreeConflictResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @GetMapping("/services/{repoId}/conflicts")
    public ResponseEntity<List<ConflictResponse>> getConflictsByRepo(@PathVariable Long repoId) {
        List<Map<String, Object>> conflicts = dependencyParserService.detectConflicts(repoId);
        List<ConflictResponse> responses = conflicts.stream()
                .map(this::toConflictResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @GetMapping("/services/{repoId}/dependencies/full-tree")
    public ResponseEntity<List<Map<String, Object>>> getFullDependencyTree(@PathVariable Long repoId) {
        Repository repo = repositoryRepository.findById(repoId).orElse(null);
        if (repo == null) {
            return ResponseEntity.notFound().build();
        }

        var tree = dependencyParserService.resolveFullDependencyTreeForRepo(repo);
        return ResponseEntity.ok(tree.stream()
                .map(dep -> Map.of(
                        "groupId", dep.getGroupId(),
                        "artifactId", dep.getArtifactId(),
                        "version", dep.getVersion(),
                        "isDirect", dep.isDirect(),
                        "depth", dep.getDepth(),
                        "transitiveDependencies", dep.getTransitiveDependencies()
                ))
                .collect(Collectors.toList()));
    }

    private DependencyResponse toResponse(DependencyRecord d) {
        return new DependencyResponse(
                d.getId(), d.getScanId(), d.getGroupId(), d.getArtifactId(),
                d.getVersion(), d.getLatestVersion(), d.getScope(),
                d.getIsDirect(), d.getIsOutdated()
        );
    }

    @SuppressWarnings("unchecked")
    private ConflictResponse toConflictResponse(Map<String, Object> map) {
        return new ConflictResponse(
                (String) map.get("groupId"),
                (String) map.get("artifactId"),
                (List<String>) map.get("versions"),
                List.of(),
                (Integer) map.getOrDefault("conflictCount", 0)
        );
    }

    @SuppressWarnings("unchecked")
    private ConflictResponse toFullTreeConflictResponse(Map<String, Object> map) {
        List<Map<String, Object>> versions = (List<Map<String, Object>>) map.get("versions");
        List<String> versionStrings = new ArrayList<>();
        List<ConflictResponse.ServiceVersion> serviceVersions = new ArrayList<>();

        for (Map<String, Object> v : versions) {
            String svcName = (String) v.get("service");
            String ver = (String) v.get("version");
            versionStrings.add(svcName + ": " + ver);
            Long svcId = v.get("serviceId") != null ? ((Number) v.get("serviceId")).longValue() : null;
            serviceVersions.add(new ConflictResponse.ServiceVersion(svcId, svcName, ver));
        }

        return new ConflictResponse(
                (String) map.get("groupId"),
                (String) map.get("artifactId"),
                versionStrings,
                serviceVersions,
                versions.size(),
                (String) map.get("recommendedVersion"),
                (String) map.get("severity"),
                (String) map.get("conflictType")
        );
    }
}

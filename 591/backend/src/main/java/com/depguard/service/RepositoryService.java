package com.depguard.service;

import com.depguard.dto.RepositoryRequest;
import com.depguard.dto.RepositoryResponse;
import com.depguard.dto.ScanResponse;
import com.depguard.entity.Repository;
import com.depguard.entity.ScanResult;
import com.depguard.enums.BuildTool;
import com.depguard.enums.ScanStatus;
import com.depguard.repository.RepositoryRepository;
import com.depguard.repository.ScanResultRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class RepositoryService {

    private final RepositoryRepository repositoryRepository;
    private final ScanResultRepository scanResultRepository;
    private final DependencyParserService dependencyParserService;
    private final VulnerabilityScanService vulnerabilityScanService;
    private final UpgradeSuggestionService upgradeSuggestionService;
    private final GitHubIntegrationService gitHubIntegrationService;

    private static final Pattern GITHUB_URL_PATTERN =
            Pattern.compile("https://github\\.com/([^/]+)/([^/]+)/?");

    @Transactional
    @CacheEvict(value = "repositories", allEntries = true)
    public RepositoryResponse addRepository(RepositoryRequest request) {
        Matcher matcher = GITHUB_URL_PATTERN.matcher(request.getGithubUrl());
        if (!matcher.find()) {
            throw new IllegalArgumentException("Invalid GitHub URL: " + request.getGithubUrl());
        }

        String owner = matcher.group(1);
        String repoName = matcher.group(2);
        String fullName = owner + "/" + repoName;

        repositoryRepository.findByFullName(fullName).ifPresent(r -> {
            throw new IllegalStateException("Repository already exists: " + fullName);
        });

        Repository repo = new Repository();
        repo.setName(repoName);
        repo.setFullName(fullName);
        repo.setHtmlUrl(request.getGithubUrl());
        repo.setDefaultBranch("main");

        if (request.getBuildTool() != null) {
            repo.setBuildTool(BuildTool.valueOf(request.getBuildTool().toUpperCase()));
        } else {
            repo.setBuildTool(detectBuildTool(owner, repoName));
        }

        repo.setScanStatus(ScanStatus.IDLE);
        repo = repositoryRepository.save(repo);
        return toResponse(repo);
    }

    @Transactional
    @CacheEvict(value = "repositories", allEntries = true)
    public void deleteRepository(Long id) {
        repositoryRepository.deleteById(id);
    }

    @Cacheable(value = "repositories")
    public List<RepositoryResponse> getAllRepositories() {
        return repositoryRepository.findAll().stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    public RepositoryResponse getRepository(Long id) {
        Repository repo = repositoryRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Repository not found: " + id));
        return toResponse(repo);
    }

    @Async
    @Transactional
    public void triggerScan(Long repoId) {
        Repository repo = repositoryRepository.findById(repoId)
                .orElseThrow(() -> new IllegalArgumentException("Repository not found: " + repoId));

        repo.setScanStatus(ScanStatus.SCANNING);
        repositoryRepository.save(repo);

        ScanResult scanResult = new ScanResult();
        scanResult.setRepoId(repoId);
        scanResult.setScanTime(LocalDateTime.now());
        scanResult.setStatus(ScanStatus.SCANNING);
        scanResult = scanResultRepository.save(scanResult);

        try {
            List<DependencyParserService.ParsedDependency> dependencies =
                    dependencyParserService.parseDependencies(repo);

            int conflictCount = dependencyParserService.detectConflicts(repoId).size();
            int outdatedCount = (int) dependencies.stream().filter(d -> Boolean.TRUE.equals(d.isOutdated())).count();

            scanResult.setTotalDeps(dependencies.size());
            scanResult.setConflictCount(conflictCount);
            scanResult.setOutdatedCount(outdatedCount);

            vulnerabilityScanService.scanVulnerabilities(scanResult.getId(), dependencies);
            upgradeSuggestionService.generateUpgradeSuggestions(repoId, dependencies);

            int vulnCount = vulnerabilityScanService.getVulnerabilityCountByScan(scanResult.getId());
            scanResult.setVulnerabilityCount(vulnCount);

            double healthScore = calculateHealthScore(dependencies.size(), conflictCount, vulnCount, outdatedCount);
            repo.setHealthScore(healthScore);

            scanResult.setStatus(ScanStatus.COMPLETED);
            repo.setScanStatus(ScanStatus.COMPLETED);
        } catch (Exception e) {
            log.error("Scan failed for repository {}: {}", repoId, e.getMessage(), e);
            scanResult.setStatus(ScanStatus.FAILED);
            repo.setScanStatus(ScanStatus.FAILED);
        }

        scanResultRepository.save(scanResult);
        repo.setLastScanTime(LocalDateTime.now());
        repositoryRepository.save(repo);
    }

    public List<ScanResponse> getScanHistory(Long repoId) {
        return scanResultRepository.findByRepoId(repoId).stream()
                .map(this::toScanResponse)
                .collect(Collectors.toList());
    }

    private BuildTool detectBuildTool(String owner, String repoName) {
        try {
            String pomContent = gitHubIntegrationService.getFileContent(owner, repoName, "pom.xml");
            if (pomContent != null) {
                return BuildTool.MAVEN;
            }
        } catch (Exception ignored) {
        }
        try {
            String gradleContent = gitHubIntegrationService.getFileContent(owner, repoName, "build.gradle");
            if (gradleContent != null) {
                return BuildTool.GRADLE;
            }
        } catch (Exception ignored) {
        }
        return BuildTool.MAVEN;
    }

    private double calculateHealthScore(int totalDeps, int conflictCount, int vulnCount, int outdatedCount) {
        if (totalDeps == 0) return 100.0;
        double conflictPenalty = conflictCount * 5.0;
        double vulnPenalty = vulnCount * 10.0;
        double outdatedPenalty = outdatedCount * 2.0;
        double score = 100.0 - conflictPenalty - vulnPenalty - outdatedPenalty;
        return Math.max(0.0, Math.min(100.0, score));
    }

    private RepositoryResponse toResponse(Repository repo) {
        return new RepositoryResponse(
                repo.getId(), repo.getName(), repo.getFullName(), repo.getHtmlUrl(),
                repo.getDefaultBranch(), repo.getBuildTool(), repo.getLastScanTime(),
                repo.getScanStatus(), repo.getHealthScore(), repo.getCreatedAt(), repo.getUpdatedAt()
        );
    }

    private ScanResponse toScanResponse(ScanResult sr) {
        return new ScanResponse(
                sr.getId(), sr.getRepoId(), sr.getScanTime(), sr.getStatus(),
                sr.getTotalDeps(), sr.getConflictCount(), sr.getVulnerabilityCount(), sr.getOutdatedCount()
        );
    }
}

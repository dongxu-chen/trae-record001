package com.depguard.controller;

import com.depguard.dto.DashboardStats;
import com.depguard.dto.VulnerabilityResponse;
import com.depguard.entity.Repository;
import com.depguard.entity.ScanResult;
import com.depguard.entity.VulnerabilityRecord;
import com.depguard.repository.RepositoryRepository;
import com.depguard.repository.DependencyRecordRepository;
import com.depguard.repository.VulnerabilityRecordRepository;
import com.depguard.repository.ScanResultRepository;
import com.depguard.service.DependencyParserService;
import com.depguard.enums.Severity;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final RepositoryRepository repositoryRepository;
    private final DependencyRecordRepository dependencyRecordRepository;
    private final VulnerabilityRecordRepository vulnerabilityRecordRepository;
    private final ScanResultRepository scanResultRepository;
    private final DependencyParserService dependencyParserService;

    @GetMapping("/stats")
    public DashboardStats getStats() {
        long totalServices = repositoryRepository.count();
        long totalDependencies = dependencyRecordRepository.count();
        long vulnerabilityCount = vulnerabilityRecordRepository.count();

        long outdatedCount = dependencyRecordRepository.findAll().stream()
                .filter(d -> Boolean.TRUE.equals(d.getIsOutdated()))
                .count();

        long conflictCount = dependencyParserService.detectConflicts(null).size();

        double healthScore = repositoryRepository.findAll().stream()
                .map(r -> r.getHealthScore() != null ? r.getHealthScore() : 0.0)
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(0.0);

        List<ScanResult> recentScansList = scanResultRepository.findAll().stream()
                .sorted(Comparator.comparing(ScanResult::getScanTime).reversed())
                .limit(5)
                .collect(Collectors.toList());

        List<DashboardStats.RecentScan> recentScans = recentScansList.stream()
                .map(scan -> {
                    String repoName = repositoryRepository.findById(scan.getRepoId())
                            .map(Repository::getName)
                            .orElse("Unknown");
                    int findings = scan.getConflictCount() + scan.getVulnerabilityCount() + scan.getOutdatedCount();
                    return new DashboardStats.RecentScan(
                            repoName,
                            scan.getScanTime().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
                            scan.getStatus(),
                            findings
                    );
                })
                .collect(Collectors.toList());

        List<VulnerabilityResponse> topVulnerabilities = vulnerabilityRecordRepository.findAll().stream()
                .sorted(Comparator.comparing(VulnerabilityRecord::getSeverity)
                        .thenComparing(VulnerabilityRecord::getCvssScore).reversed())
                .limit(3)
                .map(vuln -> {
                    VulnerabilityResponse resp = new VulnerabilityResponse();
                    resp.setCveId(vuln.getCveId());
                    resp.setSeverity(Severity.valueOf(vuln.getSeverity()));
                    resp.setCvssScore(vuln.getCvssScore());
                    resp.setDescription(vuln.getDescription());
                    resp.setAffectedVersions(vuln.getAffectedVersion());
                    resp.setFixedVersion(vuln.getFixedVersion());
                    resp.setPublishedDate(vuln.getScanId() != null ? "2024-01-15T00:00:00" : "");
                    resp.setAffectedServices(List.of());
                    return resp;
                })
                .collect(Collectors.toList());

        return new DashboardStats(
                totalServices,
                totalDependencies,
                conflictCount,
                vulnerabilityCount,
                outdatedCount,
                healthScore,
                recentScans,
                topVulnerabilities
        );
    }
}

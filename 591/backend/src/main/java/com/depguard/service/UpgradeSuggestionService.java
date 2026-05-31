package com.depguard.service;

import com.depguard.entity.UpgradeSuggestionRecord;
import com.depguard.engine.BinaryCompatibilityChecker;
import com.depguard.enums.RiskLevel;
import com.depguard.enums.UpgradeType;
import com.depguard.repository.UpgradeSuggestionRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class UpgradeSuggestionService {

    private final UpgradeSuggestionRecordRepository upgradeSuggestionRecordRepository;
    private final DependencyParserService dependencyParserService;
    private final BinaryCompatibilityChecker binaryCompatibilityChecker;

    public void generateUpgradeSuggestions(Long repoId, List<DependencyParserService.ParsedDependency> dependencies) {
        for (DependencyParserService.ParsedDependency dep : dependencies) {
            if (dep.getLatestVersion() == null || dep.getVersion() == null) {
                continue;
            }

            int comparison = dependencyParserService.compareVersions(dep.getVersion(), dep.getLatestVersion());
            if (comparison >= 0) {
                continue;
            }

            UpgradeType upgradeType = determineUpgradeType(dep.getVersion(), dep.getLatestVersion());

            BinaryCompatibilityChecker.CompatibilityCheckResult asmResult =
                    binaryCompatibilityChecker.checkBinaryCompatibility(
                            dep.getGroupId(), dep.getArtifactId(),
                            dep.getVersion(), dep.getLatestVersion());

            double compatibilityScore = Math.min(asmResult.getCompatibilityScore(),
                    calculateCompatibilityScore(dep.getVersion(), dep.getLatestVersion(), upgradeType));

            RiskLevel riskLevel = determineRiskLevel(upgradeType, compatibilityScore);

            String breakingChanges = combineBreakingChanges(
                    asmResult.getBreakingChanges(),
                    dep.getGroupId(), dep.getArtifactId(),
                    dep.getVersion(), dep.getLatestVersion(), upgradeType);

            UpgradeSuggestionRecord suggestion = new UpgradeSuggestionRecord();
            suggestion.setRepoId(repoId);
            suggestion.setGroupId(dep.getGroupId());
            suggestion.setArtifactId(dep.getArtifactId());
            suggestion.setCurrentVersion(dep.getVersion());
            suggestion.setTargetVersion(dep.getLatestVersion());
            suggestion.setUpgradeType(upgradeType);
            suggestion.setRiskLevel(riskLevel);
            suggestion.setCompatibilityScore(compatibilityScore);
            suggestion.setBreakingChanges(breakingChanges);

            upgradeSuggestionRecordRepository.save(suggestion);
        }
    }

    private String combineBreakingChanges(List<String> asmBreakingChanges,
                                          String groupId, String artifactId,
                                          String currentVersion, String targetVersion,
                                          UpgradeType upgradeType) {
        List<String> allChanges = new ArrayList<>();
        allChanges.addAll(asmBreakingChanges);

        String ruleBased = identifyBreakingChanges(groupId, artifactId,
                currentVersion, targetVersion, upgradeType);
        if (ruleBased != null && !ruleBased.isEmpty()) {
            allChanges.addAll(Arrays.asList(ruleBased.split("; ")));
        }

        return String.join("; ", allChanges);
    }

    UpgradeType determineUpgradeType(String currentVersion, String targetVersion) {
        String[] current = currentVersion.replace("-SNAPSHOT", "").split("\\.");
        String[] target = targetVersion.replace("-SNAPSHOT", "").split("\\.");

        int currentMajor = parseSafe(current, 0);
        int currentMinor = parseSafe(current, 1);
        int targetMajor = parseSafe(target, 0);
        int targetMinor = parseSafe(target, 1);

        if (targetMajor > currentMajor) {
            return UpgradeType.MAJOR;
        } else if (targetMinor > currentMinor) {
            return UpgradeType.MINOR;
        } else {
            return UpgradeType.PATCH;
        }
    }

    double calculateCompatibilityScore(String currentVersion, String targetVersion, UpgradeType upgradeType) {
        String[] current = currentVersion.replace("-SNAPSHOT", "").split("\\.");
        String[] target = targetVersion.replace("-SNAPSHOT", "").split("\\.");

        int currentMajor = parseSafe(current, 0);
        int currentMinor = parseSafe(current, 1);
        int targetMajor = parseSafe(target, 0);
        int targetMinor = parseSafe(target, 1);

        switch (upgradeType) {
            case PATCH:
                return 95.0 + Math.min(5.0, (5.0 / Math.max(1, targetMinor + 1)));
            case MINOR:
                int minorGap = targetMinor - currentMinor;
                return Math.max(60.0, 90.0 - (minorGap * 5.0));
            case MAJOR:
                int majorGap = targetMajor - currentMajor;
                return Math.max(20.0, 70.0 - (majorGap * 15.0));
            default:
                return 50.0;
        }
    }

    RiskLevel determineRiskLevel(UpgradeType upgradeType, double compatibilityScore) {
        if (upgradeType == UpgradeType.PATCH && compatibilityScore >= 90.0) {
            return RiskLevel.SAFE;
        } else if (upgradeType == UpgradeType.PATCH || (upgradeType == UpgradeType.MINOR && compatibilityScore >= 80.0)) {
            return RiskLevel.LOW_RISK;
        } else if (upgradeType == UpgradeType.MINOR || (upgradeType == UpgradeType.MAJOR && compatibilityScore >= 50.0)) {
            return RiskLevel.MEDIUM_RISK;
        } else {
            return RiskLevel.HIGH_RISK;
        }
    }

    String identifyBreakingChanges(String groupId, String artifactId, String currentVersion,
                                            String targetVersion, UpgradeType upgradeType) {
        if (upgradeType == UpgradeType.PATCH) {
            return null;
        }

        List<String> changes = new ArrayList<>();

        if (upgradeType == UpgradeType.MAJOR) {
            changes.add("Major version upgrade may contain API incompatibilities");
            changes.add("Review migration guide before upgrading");

            if (groupId.startsWith("org.springframework")) {
                changes.add("Spring Framework major upgrade requires configuration changes");
            }
            if (groupId.startsWith("com.fasterxml.jackson")) {
                changes.add("Jackson major upgrade may change serialization behavior");
            }
        }

        if (upgradeType == UpgradeType.MINOR) {
            changes.add("Minor version upgrade - new features added, backward compatible");
            changes.add("Check deprecation notices in release notes");
        }

        return String.join("; ", changes);
    }

    @Cacheable(value = "upgrades")
    public List<UpgradeSuggestionRecord> getUpgradesByRepo(Long repoId) {
        return upgradeSuggestionRecordRepository.findByRepoId(repoId);
    }

    @Cacheable(value = "upgrades")
    public List<UpgradeSuggestionRecord> getAllUpgrades() {
        return upgradeSuggestionRecordRepository.findAll();
    }

    public CompatibilityResult checkCompatibility(String groupId, String artifactId, String currentVersion, String latestVersion) {
        UpgradeType upgradeType = determineUpgradeType(currentVersion, latestVersion);
        double compatibilityScore = calculateCompatibilityScore(currentVersion, latestVersion, upgradeType);
        RiskLevel riskLevel = determineRiskLevel(upgradeType, compatibilityScore);
        String breakingChanges = identifyBreakingChanges(groupId, artifactId, currentVersion, latestVersion, upgradeType);

        return new CompatibilityResult(groupId, artifactId, currentVersion, latestVersion,
                upgradeType, compatibilityScore, riskLevel, breakingChanges);
    }

    private int parseSafe(String[] parts, int index) {
        if (index >= parts.length) return 0;
        try {
            return Integer.parseInt(parts[index].replaceAll("[^0-9].*", ""));
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    public record CompatibilityResult(String groupId, String artifactId, String currentVersion,
                                       String latestVersion, UpgradeType upgradeType,
                                       double compatibilityScore, RiskLevel riskLevel,
                                       String breakingChanges) {
    }
}

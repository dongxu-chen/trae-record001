package com.datacheck.service;

import com.datacheck.check.CheckEngine;
import com.datacheck.model.CheckReport;
import com.datacheck.model.CheckResult;
import com.datacheck.model.CheckTask;
import com.datacheck.model.DiffResult;
import com.datacheck.model.enums.DiffType;
import com.datacheck.model.enums.RepairStatus;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ReportService {

    private final CheckEngine checkEngine;

    private final Cache<String, CheckReport> reportCache = Caffeine.newBuilder()
            .expireAfterWrite(24, TimeUnit.HOURS)
            .maximumSize(200)
            .build();

    @Autowired
    public ReportService(CheckEngine checkEngine) {
        this.checkEngine = checkEngine;
    }

    public CheckReport generateReport(String taskId) {
        Optional<CheckResult> resultOpt = checkEngine.getResult(taskId);
        if (resultOpt.isEmpty()) {
            log.warn("No check result found for task: {}", taskId);
            return null;
        }

        CheckResult result = resultOpt.get();
        List<DiffResult> diffs = result.getDiffs();

        CheckReport.SummarySection summary = buildSummary(result, diffs);
        CheckReport.DiffStatistics diffStats = buildDiffStatistics(diffs);
        CheckReport.RepairStatistics repairStats = buildRepairStatistics(diffs);
        List<CheckReport.DiffDetail> diffDetails = buildDiffDetails(diffs);
        List<CheckReport.RepairRecord> repairRecords = buildRepairRecords(diffs);

        CheckReport report = CheckReport.builder()
                .id(UUID.randomUUID().toString())
                .taskId(taskId)
                .sourceType(result.getSourceType())
                .tableName(result.getTableName())
                .checkMode(result.getCheckMode())
                .generatedAt(LocalDateTime.now())
                .summary(summary)
                .diffStatistics(diffStats)
                .repairStatistics(repairStats)
                .diffDetails(diffDetails)
                .repairRecords(repairRecords)
                .metadata(result.getMetrics())
                .build();

        reportCache.put(report.getId(), report);
        log.info("Generated report {} for task {}", report.getId(), taskId);
        return report;
    }

    public CheckReport generateLatestReport() {
        Collection<CheckResult> results = checkEngine.getRecentResults();
        if (results.isEmpty()) {
            return null;
        }

        CheckResult latest = results.stream()
                .max(Comparator.comparing(CheckResult::getEndTime))
                .orElse(null);

        if (latest == null) {
            return null;
        }

        return generateReport(latest.getTaskId());
    }

    public Collection<CheckReport> getAllReports() {
        return reportCache.asMap().values();
    }

    public Optional<CheckReport> getReport(String reportId) {
        return Optional.ofNullable(reportCache.getIfPresent(reportId));
    }

    private CheckReport.SummarySection buildSummary(CheckResult result, List<DiffResult> diffs) {
        long totalRepaired = diffs.stream()
                .filter(d -> d.getRepairStatus() == RepairStatus.SUCCESS)
                .count();
        long totalFailed = diffs.stream()
                .filter(d -> d.getRepairStatus() == RepairStatus.FAILED)
                .count();
        long totalPending = diffs.stream()
                .filter(d -> d.getRepairStatus() == RepairStatus.PENDING ||
                        d.getRepairStatus() == RepairStatus.IN_PROGRESS)
                .count();

        double diffRate = result.getTotalSourceRecords() > 0 ?
                (double) diffs.size() / result.getTotalSourceRecords() : 0;
        double repairRate = diffs.size() > 0 ?
                (double) totalRepaired / diffs.size() : 0;

        long durationMs = 0;
        if (result.getStartTime() != null && result.getEndTime() != null) {
            durationMs = ChronoUnit.MILLIS.between(result.getStartTime(), result.getEndTime());
        }

        long hashVerified = result.getMetrics() != null ?
                ((Number) result.getMetrics().getOrDefault("hashVerifiedRecords", 0L)).longValue() : 0;
        long hashSkipped = result.getMetrics() != null ?
                ((Number) result.getMetrics().getOrDefault("hashSkippedRecords", 0L)).longValue() : 0;

        return CheckReport.SummarySection.builder()
                .totalSourceRecords(result.getTotalSourceRecords())
                .totalTargetRecords(result.getTotalTargetRecords())
                .totalDiffs(diffs.size())
                .totalRepaired(totalRepaired)
                .totalPendingRepair(totalPending)
                .totalFailedRepair(totalFailed)
                .repairRate(repairRate)
                .diffRate(diffRate)
                .avgLatencyMs(result.getAvgLatencyMs())
                .maxLatencyMs(result.getMaxLatencyMs())
                .durationMs(durationMs)
                .hashVerifiedRecords(hashVerified)
                .hashSkippedRecords(hashSkipped)
                .build();
    }

    private CheckReport.DiffStatistics buildDiffStatistics(List<DiffResult> diffs) {
        long missingInTarget = diffs.stream()
                .filter(d -> d.getDiffType() == DiffType.MISSING_IN_TARGET).count();
        long missingInSource = diffs.stream()
                .filter(d -> d.getDiffType() == DiffType.MISSING_IN_SOURCE).count();
        long valueMismatch = diffs.stream()
                .filter(d -> d.getDiffType() == DiffType.VALUE_MISMATCH).count();
        long latencyExceeded = diffs.stream()
                .filter(d -> d.getDiffType() == DiffType.LATENCY_EXCEEDED).count();

        Map<String, Long> diffByTable = diffs.stream()
                .filter(d -> d.getTableName() != null)
                .collect(Collectors.groupingBy(DiffResult::getTableName, Collectors.counting()));

        Map<String, Long> diffByHour = new LinkedHashMap<>();
        for (DiffResult diff : diffs) {
            if (diff.getDetectedAt() != null) {
                String hourKey = diff.getDetectedAt().truncatedTo(ChronoUnit.HOURS)
                        .toString().substring(0, 16);
                diffByHour.merge(hourKey, 1L, Long::sum);
            }
        }

        List<CheckReport.TopDiffField> topFields = new ArrayList<>();
        Map<String, Long> fieldCounts = new HashMap<>();
        for (DiffResult diff : diffs) {
            if (diff.getDiffFields() != null) {
                for (String field : diff.getDiffFields().keySet()) {
                    fieldCounts.merge(field, 1L, Long::sum);
                }
            }
        }
        fieldCounts.entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(10)
                .forEach(entry -> topFields.add(CheckReport.TopDiffField.builder()
                        .fieldName(entry.getKey())
                        .count(entry.getValue())
                        .percentage(diffs.size() > 0 ?
                                (double) entry.getValue() / diffs.size() * 100 : 0)
                        .build()));

        return CheckReport.DiffStatistics.builder()
                .missingInTargetCount(missingInTarget)
                .missingInSourceCount(missingInSource)
                .valueMismatchCount(valueMismatch)
                .latencyExceededCount(latencyExceeded)
                .diffByTable(diffByTable)
                .diffByHour(diffByHour)
                .topDiffFields(topFields)
                .build();
    }

    private CheckReport.RepairStatistics buildRepairStatistics(List<DiffResult> diffs) {
        long totalRepairs = diffs.stream()
                .filter(d -> d.getRepairStatus() != RepairStatus.PENDING).count();
        long successCount = diffs.stream()
                .filter(d -> d.getRepairStatus() == RepairStatus.SUCCESS).count();
        long failedCount = diffs.stream()
                .filter(d -> d.getRepairStatus() == RepairStatus.FAILED).count();

        Map<DiffType, Long> repairByType = diffs.stream()
                .filter(d -> d.getRepairStatus() != RepairStatus.PENDING)
                .collect(Collectors.groupingBy(DiffResult::getDiffType, Collectors.counting()));

        Map<RepairStatus, Long> repairByStatus = diffs.stream()
                .collect(Collectors.groupingBy(DiffResult::getRepairStatus, Collectors.counting()));

        return CheckReport.RepairStatistics.builder()
                .totalRepairs(totalRepairs)
                .successCount(successCount)
                .failedCount(failedCount)
                .successRate(totalRepairs > 0 ? (double) successCount / totalRepairs : 0)
                .repairByType(repairByType)
                .repairByStatus(repairByStatus)
                .build();
    }

    private List<CheckReport.DiffDetail> buildDiffDetails(List<DiffResult> diffs) {
        return diffs.stream()
                .limit(1000)
                .map(d -> CheckReport.DiffDetail.builder()
                        .diffId(d.getId())
                        .key(d.getKey())
                        .diffType(d.getDiffType())
                        .diffFields(d.getDiffFields())
                        .latencyMs(d.getLatencyMs())
                        .detectedAt(d.getDetectedAt())
                        .build())
                .collect(Collectors.toList());
    }

    private List<CheckReport.RepairRecord> buildRepairRecords(List<DiffResult> diffs) {
        return diffs.stream()
                .filter(d -> d.getRepairStatus() != RepairStatus.PENDING)
                .limit(1000)
                .map(d -> CheckReport.RepairRecord.builder()
                        .diffId(d.getId())
                        .key(d.getKey())
                        .diffType(d.getDiffType())
                        .repairStatus(d.getRepairStatus())
                        .repairAttempts(d.getRepairAttempts())
                        .repairErrorMessage(d.getRepairErrorMessage())
                        .repairedAt(d.getDetectedAt())
                        .build())
                .collect(Collectors.toList());
    }
}

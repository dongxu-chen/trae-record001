package com.alert.service;

import com.alert.dto.ReportDTO;
import com.alert.entity.AlertEvent;
import com.alert.enums.AlertSeverity;
import com.alert.enums.AlertStatus;
import com.alert.repository.AlertEventRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ReportService {

    @Autowired
    private AlertEventRepository alertEventRepository;

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    public ReportDTO generateReport(int days) {
        LocalDateTime endTime = LocalDateTime.now();
        LocalDateTime startTime = endTime.minusDays(days);

        List<AlertEvent> alerts = alertEventRepository.findAll().stream()
                .filter(a -> a.getCreateTime().isAfter(startTime) && a.getCreateTime().isBefore(endTime))
                .collect(Collectors.toList());

        ReportDTO report = new ReportDTO();
        report.setTimeRange(startTime.format(DATE_FORMATTER) + " ~ " + endTime.format(DATE_FORMATTER);
        report.setTotalAlerts((long) alerts.size());

        List<AlertEvent> resolvedAlerts = alerts.stream()
                .filter(a -> a.getStatus() == AlertStatus.RESOLVED || a.getStatus() == AlertStatus.CLOSED)
                .collect(Collectors.toList());
        report.setResolvedAlerts((long) resolvedAlerts.size());

        report.setAvgMttrMinutes(calculateAvgMTTR(resolvedAlerts));

        report.setAlertBySeverity(countBySeverity(alerts));

        report.setAlertByStatus(countByStatus(alerts));

        report.setAlertBySource(countBySource(alerts));

        report.setDailyTrend(calculateDailyTrend(alerts, startTime, days));

        report.setHourlyTrend(calculateHourlyTrend(alerts));

        report.setTopHosts(getTopHosts(alerts, 10));

        report.setTopServices(getTopServices(alerts, 10));

        report.setRootCauseAnalysis(analyzeRootCauses(alerts));

        report.setSlaCompliance(calculateSLACompliance(resolvedAlerts, 60));

        return report;
    }

    private Double calculateAvgMTTR(List<AlertEvent> resolvedAlerts) {
        if (resolvedAlerts.isEmpty()) return 0.0;

        double totalMinutes = resolvedAlerts.stream()
                .filter(a -> a.getResolveTime() != null)
                .mapToDouble(a -> {
                    long seconds = java.time.Duration.between(a.getCreateTime(), a.getResolveTime()).toMinutes();
                    return (double) seconds;
                })
                .average()
                .orElse(0.0);

        return Math.round(totalMinutes * 100) / 100.0;
    }

    private Map<String, Long> countBySeverity(List<AlertEvent> alerts) {
        Map<String, Long> result = new LinkedHashMap<>();
        for (AlertSeverity s : AlertSeverity.values()) {
            long count = alerts.stream()
                    .filter(a -> a.getSeverity() == s)
                    .count();
            if (count > 0) {
                result.put(s.getCode(), count);
            }
        }
        return result;
    }

    private Map<String, Long> countByStatus(List<AlertEvent> alerts) {
        return alerts.stream()
                .collect(Collectors.groupingBy(
                        a -> a.getStatus().getCode(),
                        LinkedHashMap::new,
                        Collectors.counting()
                ));
    }

    private Map<String, Long> countBySource(List<AlertEvent> alerts) {
        return alerts.stream()
                .filter(a -> a.getSource() != null && !a.getSource().isEmpty())
                .collect(Collectors.groupingBy(
                        AlertEvent::getSource,
                        Collectors.counting()
                ))
                .entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(10)
                .collect(Collectors.toMap(
                        Map.Entry::getKey,
                        Map.Entry::getValue,
                        (e1, e2) -> e1,
                        LinkedHashMap::new
                ));
    }

    private List<ReportDTO.DailyTrend> calculateDailyTrend(List<AlertEvent> alerts, LocalDateTime startTime, int days) {
        Map<String, Long> dailyCounts = new LinkedHashMap<>();
        Map<String, Long> dailyResolved = new LinkedHashMap<>();

        for (int i = 0; i < days; i++) {
            String date = startTime.plusDays(i).format(DATE_FORMATTER);
            dailyCounts.put(date, 0L);
            dailyResolved.put(date, 0L);
        }

        for (AlertEvent alert : alerts) {
            String date = alert.getCreateTime().format(DATE_FORMATTER);
            dailyCounts.merge(date, 1L, Long::sum);

            if (alert.getStatus() == AlertStatus.RESOLVED || alert.getStatus() == AlertStatus.CLOSED) {
                String resolveDate = (alert.getResolveTime() != null) ?
                        alert.getResolveTime().format(DATE_FORMATTER) : date;
                dailyResolved.merge(resolveDate, 1L, Long::sum);
            }
        }

        return dailyCounts.entrySet().stream()
                .map(entry -> {
                    ReportDTO.DailyTrend trend = new ReportDTO.DailyTrend();
                    trend.setDate(entry.getKey());
                    trend.setCount(entry.getValue());
                    trend.setResolved(dailyResolved.getOrDefault(entry.getKey(), 0L));
                    return trend;
                })
                .collect(Collectors.toList());
    }

    private List<ReportDTO.HourlyTrend> calculateHourlyTrend(List<AlertEvent> alerts) {
        Map<Integer, List<AlertEvent>> hourlyAlerts = alerts.stream()
                .collect(Collectors.groupingBy(a -> a.getCreateTime().getHour()));

        List<ReportDTO.HourlyTrend> result = new ArrayList<>();

        for (int hour = 0; hour < 24; hour++) {
            ReportDTO.HourlyTrend trend = new ReportDTO.HourlyTrend();
            trend.setHour(hour);
            List<AlertEvent> hourAlerts = hourlyAlerts.getOrDefault(hour, Collections.emptyList());
            trend.setAvgCount((double) hourAlerts.size() / 7);
            result.add(trend);
        }

        return result;
    }

    private List<String> getTopHosts(List<AlertEvent> alerts, int limit) {
        return alerts.stream()
                .filter(a -> a.getHost() != null && !a.getHost().isEmpty())
                .collect(Collectors.groupingBy(AlertEvent::getHost, Collectors.counting()))
                .entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(limit)
                .map(e -> e.getKey() + " (" + e.getValue() + ")")
                .collect(Collectors.toList());
    }

    private List<String> getTopServices(List<AlertEvent> alerts, int limit) {
        return alerts.stream()
                .filter(a -> a.getService() != null && !a.getService().isEmpty())
                .collect(Collectors.groupingBy(AlertEvent::getService, Collectors.counting()))
                .entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(limit)
                .map(e -> e.getKey() + " (" + e.getValue() + ")")
                .collect(Collectors.toList());
    }

    private List<ReportDTO.RootCauseSummary> analyzeRootCauses(List<AlertEvent> alerts) {
        Map<String, List<AlertEvent>> hostGroups = alerts.stream()
                .filter(a -> a.getHost() != null && !a.getHost().isEmpty())
                .collect(Collectors.groupingBy(AlertEvent::getHost));

        return hostGroups.entrySet().stream()
                .filter(e -> e.getValue().size() >= 3)
                .map(entry -> {
                    ReportDTO.RootCauseSummary summary = new ReportDTO.RootCauseSummary();
                    summary.setRootCause("Host: " + entry.getKey());
                    summary.setCount((long) entry.getValue().size());
                    summary.setAvgMttr(calculateAvgMTTR(entry.getValue().stream()
                            .filter(a -> a.getStatus() == AlertStatus.RESOLVED || a.getStatus() == AlertStatus.CLOSED)
                            .collect(Collectors.toList())));
                    return summary;
                })
                .sorted((a, b) -> Long.compare(b.getCount(), a.getCount()))
                .limit(5)
                .collect(Collectors.toList());
    }

    private Double calculateSLACompliance(List<AlertEvent> resolvedAlerts, int targetMinutes) {
        if (resolvedAlerts.isEmpty()) return 100.0;

        long compliantCount = resolvedAlerts.stream()
                .filter(a -> a.getResolveTime() != null)
                .filter(a -> {
                    long minutes = java.time.Duration.between(a.getCreateTime(), a.getResolveTime()).toMinutes();
                    return minutes <= targetMinutes;
                })
                .count();

        double compliance = (double) compliantCount / resolvedAlerts.size() * 100;
        return Math.round(compliance * 100) / 100.0;
    }
}

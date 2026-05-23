package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.DeliveryReport;
import com.emailmarketing.entity.EmailSendLog;
import com.emailmarketing.mapper.DeliveryReportMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;

@Slf4j
@Service
public class DeliveryReportService extends ServiceImpl<DeliveryReportMapper, DeliveryReport> {

    @Autowired
    private EmailSendLogService sendLogService;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Transactional(rollbackFor = Exception.class)
    public void generateDailyReport(LocalDate reportDate) {
        LocalDateTime startOfDay = reportDate.atStartOfDay();
        LocalDateTime endOfDay = reportDate.atTime(23, 59, 59);

        LambdaQueryWrapper<EmailSendLog> wrapper = new LambdaQueryWrapper<>();
        wrapper.ge(EmailSendLog::getCreatedAt, startOfDay);
        wrapper.le(EmailSendLog::getCreatedAt, endOfDay);
        List<EmailSendLog> logs = sendLogService.list(wrapper);

        Map<String, List<EmailSendLog>> domainGroups = new HashMap<>();
        for (EmailSendLog log : logs) {
            String domain = extractDomain(log.getEmail());
            domainGroups.computeIfAbsent(domain, k -> new ArrayList<>()).add(log);
        }

        for (Map.Entry<String, List<EmailSendLog>> entry : domainGroups.entrySet()) {
            String domain = entry.getKey();
            List<EmailSendLog> domainLogs = entry.getValue();
            saveDomainReport(null, domain, reportDate, domainLogs);
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public void generateTaskReport(Long taskId, LocalDate reportDate) {
        LocalDateTime startOfDay = reportDate.atStartOfDay();
        LocalDateTime endOfDay = reportDate.atTime(23, 59, 59);

        LambdaQueryWrapper<EmailSendLog> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(EmailSendLog::getTaskId, taskId);
        wrapper.ge(EmailSendLog::getCreatedAt, startOfDay);
        wrapper.le(EmailSendLog::getCreatedAt, endOfDay);
        List<EmailSendLog> logs = sendLogService.list(wrapper);

        Map<String, List<EmailSendLog>> domainGroups = new HashMap<>();
        for (EmailSendLog log : logs) {
            String domain = extractDomain(log.getEmail());
            domainGroups.computeIfAbsent(domain, k -> new ArrayList<>()).add(log);
        }

        for (Map.Entry<String, List<EmailSendLog>> entry : domainGroups.entrySet()) {
            String domain = entry.getKey();
            List<EmailSendLog> domainLogs = entry.getValue();
            saveDomainReport(taskId, domain, reportDate, domainLogs);
        }
    }

    private void saveDomainReport(Long taskId, String domain, LocalDate reportDate, List<EmailSendLog> logs) {
        int totalSent = logs.size();
        int delivered = (int) logs.stream().filter(l -> l.getSendStatus() == 1).count();
        int bounced = (int) logs.stream().filter(l -> l.getSendStatus() == 2).count();
        int opened = (int) logs.stream().filter(l -> l.getOpened() == 1).count();
        int clicked = (int) logs.stream().filter(l -> l.getClicked() == 1).count();

        Map<String, Integer> delayDistribution = calculateDelayDistribution(logs);
        int avgDelay = calculateAverageDelay(logs);

        LambdaQueryWrapper<DeliveryReport> wrapper = new LambdaQueryWrapper<>();
        if (taskId != null) {
            wrapper.eq(DeliveryReport::getTaskId, taskId);
        } else {
            wrapper.isNull(DeliveryReport::getTaskId);
        }
        wrapper.eq(DeliveryReport::getDomain, domain);
        wrapper.eq(DeliveryReport::getReportDate, reportDate);

        DeliveryReport report = getOne(wrapper);
        if (report == null) {
            report = new DeliveryReport();
            report.setTaskId(taskId);
            report.setDomain(domain);
            report.setReportDate(reportDate);
            report.setCreatedAt(LocalDateTime.now());
        }

        report.setTotalSent(totalSent);
        report.setDelivered(delivered);
        report.setBounced(bounced);
        report.setComplained(0);
        report.setOpened(opened);
        report.setClicked(clicked);
        report.setDeliveryRate(calculateRate(delivered, totalSent));
        report.setOpenRate(calculateRate(opened, delivered));
        report.setClickRate(calculateRate(clicked, opened));
        report.setAvgDelaySeconds(avgDelay);
        report.setDelayDistribution(toJson(delayDistribution));
        report.setUpdatedAt(LocalDateTime.now());

        saveOrUpdate(report);
    }

    private Map<String, Integer> calculateDelayDistribution(List<EmailSendLog> logs) {
        Map<String, Integer> distribution = new LinkedHashMap<>();
        distribution.put("0-10s", 0);
        distribution.put("10-30s", 0);
        distribution.put("30-60s", 0);
        distribution.put("1-5m", 0);
        distribution.put("5m+", 0);

        for (EmailSendLog log : logs) {
            if (log.getSentAt() != null && log.getCreatedAt() != null) {
                long seconds = ChronoUnit.SECONDS.between(log.getCreatedAt(), log.getSentAt());
                if (seconds < 10) {
                    distribution.merge("0-10s", 1, Integer::sum);
                } else if (seconds < 30) {
                    distribution.merge("10-30s", 1, Integer::sum);
                } else if (seconds < 60) {
                    distribution.merge("30-60s", 1, Integer::sum);
                } else if (seconds < 300) {
                    distribution.merge("1-5m", 1, Integer::sum);
                } else {
                    distribution.merge("5m+", 1, Integer::sum);
                }
            }
        }
        return distribution;
    }

    private int calculateAverageDelay(List<EmailSendLog> logs) {
        long totalSeconds = 0;
        int count = 0;

        for (EmailSendLog log : logs) {
            if (log.getSentAt() != null && log.getCreatedAt() != null) {
                totalSeconds += ChronoUnit.SECONDS.between(log.getCreatedAt(), log.getSentAt());
                count++;
            }
        }

        return count > 0 ? (int) (totalSeconds / count) : 0;
    }

    private BigDecimal calculateRate(int numerator, int denominator) {
        if (denominator == 0) {
            return BigDecimal.ZERO;
        }
        return BigDecimal.valueOf(numerator)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(denominator), 2, RoundingMode.HALF_UP);
    }

    private String extractDomain(String email) {
        int atIndex = email.indexOf('@');
        if (atIndex > 0 && atIndex < email.length() - 1) {
            return email.substring(atIndex + 1).toLowerCase();
        }
        return "unknown";
    }

    private String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (Exception e) {
            return "{}";
        }
    }

    @Scheduled(cron = "0 30 1 * * ?")
    public void autoGenerateDailyReport() {
        LocalDate yesterday = LocalDate.now().minusDays(1);
        try {
            generateDailyReport(yesterday);
            log.info("Generated daily delivery report for {}", yesterday);
        } catch (Exception e) {
            log.error("Failed to generate daily delivery report", e);
        }
    }

    public List<DeliveryReport> getDomainReportSummary(LocalDate startDate, LocalDate endDate) {
        LambdaQueryWrapper<DeliveryReport> wrapper = new LambdaQueryWrapper<>();
        wrapper.between(DeliveryReport::getReportDate, startDate, endDate);
        wrapper.isNull(DeliveryReport::getTaskId);
        wrapper.orderByAsc(DeliveryReport::getReportDate);
        return list(wrapper);
    }

    public List<DeliveryReport> getTaskReport(Long taskId, LocalDate startDate, LocalDate endDate) {
        LambdaQueryWrapper<DeliveryReport> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(DeliveryReport::getTaskId, taskId);
        wrapper.between(DeliveryReport::getReportDate, startDate, endDate);
        wrapper.orderByAsc(DeliveryReport::getReportDate);
        return list(wrapper);
    }

    public Map<String, Object> getOverallDeliveryStats(LocalDate startDate, LocalDate endDate) {
        List<DeliveryReport> reports = getDomainReportSummary(startDate, endDate);

        Map<String, Object> stats = new HashMap<>();
        Map<String, Map<String, Object>> domainStats = new HashMap<>();

        int totalSent = 0, totalDelivered = 0, totalOpened = 0, totalClicked = 0;

        for (DeliveryReport report : reports) {
            totalSent += report.getTotalSent();
            totalDelivered += report.getDelivered();
            totalOpened += report.getOpened();
            totalClicked += report.getClicked();

            String domain = report.getDomain();
            domainStats.computeIfAbsent(domain, k -> new HashMap<>()).merge(
                    "totalSent", report.getTotalSent(), Integer::sum);
            domainStats.computeIfAbsent(domain, k -> new HashMap<>()).merge(
                    "delivered", report.getDelivered(), Integer::sum);
            domainStats.computeIfAbsent(domain, k -> new HashMap<>()).merge(
                    "opened", report.getOpened(), Integer::sum);
        }

        stats.put("totalSent", totalSent);
        stats.put("totalDelivered", totalDelivered);
        stats.put("totalOpened", totalOpened);
        stats.put("totalClicked", totalClicked);
        stats.put("overallDeliveryRate", calculateRate(totalDelivered, totalSent));
        stats.put("overallOpenRate", calculateRate(totalOpened, totalDelivered));
        stats.put("overallClickRate", calculateRate(totalClicked, totalOpened));
        stats.put("domainStats", domainStats);

        return stats;
    }
}

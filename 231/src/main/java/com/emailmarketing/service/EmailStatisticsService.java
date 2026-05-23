package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.EmailSendLog;
import com.emailmarketing.entity.EmailStatistics;
import com.emailmarketing.entity.EmailTask;
import com.emailmarketing.mapper.EmailStatisticsMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class EmailStatisticsService extends ServiceImpl<EmailStatisticsMapper, EmailStatistics> {

    @Autowired
    private EmailSendLogService sendLogService;

    @Autowired
    private EmailTaskService taskService;

    public EmailStatistics getTaskStatistics(Long taskId) {
        LocalDate today = LocalDate.now();
        LambdaQueryWrapper<EmailStatistics> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(EmailStatistics::getTaskId, taskId);
        wrapper.eq(EmailStatistics::getStatisticsDate, today);
        EmailStatistics stats = getOne(wrapper);
        
        if (stats == null) {
            stats = calculateAndSaveStatistics(taskId, today);
        }
        
        return stats;
    }

    public List<EmailStatistics> getTaskStatisticsByDateRange(Long taskId, LocalDate startDate, LocalDate endDate) {
        LambdaQueryWrapper<EmailStatistics> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(EmailStatistics::getTaskId, taskId);
        wrapper.between(EmailStatistics::getStatisticsDate, startDate, endDate);
        wrapper.orderByAsc(EmailStatistics::getStatisticsDate);
        return list(wrapper);
    }

    @Scheduled(cron = "0 0 * * * ?")
    public void hourlyStatisticsUpdate() {
        List<EmailTask> tasks = taskService.list();
        LocalDate today = LocalDate.now();
        
        for (EmailTask task : tasks) {
            if (task.getStatus() == 1 || task.getStatus() == 2) {
                calculateAndSaveStatistics(task.getId(), today);
            }
        }
    }

    private EmailStatistics calculateAndSaveStatistics(Long taskId, LocalDate date) {
        LocalDateTime startOfDay = date.atStartOfDay();
        LocalDateTime endOfDay = date.atTime(23, 59, 59);

        LambdaQueryWrapper<EmailSendLog> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(EmailSendLog::getTaskId, taskId);
        wrapper.ge(EmailSendLog::getCreatedAt, startOfDay);
        wrapper.le(EmailSendLog::getCreatedAt, endOfDay);
        
        List<EmailSendLog> logs = sendLogService.list(wrapper);
        
        int totalSent = (int) logs.stream().filter(log -> log.getSendStatus() == 1).count();
        int totalOpened = (int) logs.stream().filter(log -> log.getOpened() == 1).count();
        int totalClicked = (int) logs.stream().filter(log -> log.getClicked() == 1).count();
        int totalUnsubscribed = (int) logs.stream().filter(log -> log.getUnsubscribed() == 1).count();

        BigDecimal openRate = calculateRate(totalOpened, totalSent);
        BigDecimal clickRate = calculateRate(totalClicked, totalSent);
        BigDecimal unsubscribeRate = calculateRate(totalUnsubscribed, totalSent);

        LambdaQueryWrapper<EmailStatistics> statsWrapper = new LambdaQueryWrapper<>();
        statsWrapper.eq(EmailStatistics::getTaskId, taskId);
        statsWrapper.eq(EmailStatistics::getStatisticsDate, date);
        EmailStatistics stats = getOne(statsWrapper);

        if (stats == null) {
            stats = new EmailStatistics();
            stats.setTaskId(taskId);
            stats.setStatisticsDate(date);
            stats.setCreatedAt(LocalDateTime.now());
        }

        stats.setTotalSent(totalSent);
        stats.setTotalOpened(totalOpened);
        stats.setTotalClicked(totalClicked);
        stats.setTotalUnsubscribed(totalUnsubscribed);
        stats.setOpenRate(openRate);
        stats.setClickRate(clickRate);
        stats.setUnsubscribeRate(unsubscribeRate);
        stats.setUpdatedAt(LocalDateTime.now());

        saveOrUpdate(stats);
        return stats;
    }

    private BigDecimal calculateRate(int numerator, int denominator) {
        if (denominator == 0) {
            return BigDecimal.ZERO;
        }
        return BigDecimal.valueOf(numerator)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(denominator), 2, RoundingMode.HALF_UP);
    }
}

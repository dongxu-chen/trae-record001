package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.sms.platform.entity.SmsSendRecord;
import com.sms.platform.mapper.SmsSendRecordMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.*;

@Slf4j
@Service
public class SmsSendRecordService {

    @Resource
    private SmsSendRecordMapper sendRecordMapper;

    public Page<SmsSendRecord> listRecords(Integer pageNum, Integer pageSize, String mobile, Integer smsType,
                                           Integer channelCode, Integer status, LocalDateTime startTime, LocalDateTime endTime) {
        Page<SmsSendRecord> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<SmsSendRecord> wrapper = new LambdaQueryWrapper<SmsSendRecord>()
                .eq(SmsSendRecord::getDeleted, 0)
                .orderByDesc(SmsSendRecord::getCreateTime);

        if (mobile != null && !mobile.isEmpty()) {
            wrapper.eq(SmsSendRecord::getMobile, mobile);
        }
        if (smsType != null) {
            wrapper.eq(SmsSendRecord::getSmsType, smsType);
        }
        if (channelCode != null) {
            wrapper.eq(SmsSendRecord::getChannelCode, channelCode);
        }
        if (status != null) {
            wrapper.eq(SmsSendRecord::getStatus, status);
        }
        if (startTime != null) {
            wrapper.ge(SmsSendRecord::getCreateTime, startTime);
        }
        if (endTime != null) {
            wrapper.le(SmsSendRecord::getCreateTime, endTime);
        }

        return sendRecordMapper.selectPage(page, wrapper);
    }

    public SmsSendRecord getRecord(Long id) {
        return sendRecordMapper.selectById(id);
    }

    public SmsSendRecord getRecordBySerialNo(String serialNo) {
        return sendRecordMapper.selectOne(
                new LambdaQueryWrapper<SmsSendRecord>()
                        .eq(SmsSendRecord::getSerialNo, serialNo)
                        .eq(SmsSendRecord::getDeleted, 0)
        );
    }

    public Map<String, Object> getStatistics(LocalDate startDate, LocalDate endDate) {
        LocalDateTime startTime = startDate != null ? startDate.atStartOfDay() : LocalDate.now().atStartOfDay();
        LocalDateTime endTime = endDate != null ? endDate.atTime(LocalTime.MAX) : LocalDate.now().atTime(LocalTime.MAX);

        Map<String, Object> result = new HashMap<>();
        Map<String, Object> overall = sendRecordMapper.selectStatistics(startTime, endTime);

        if (overall != null) {
            result.put("total", overall.get("total"));
            result.put("successCount", overall.get("successCount"));
            result.put("failCount", overall.get("failCount"));
            result.put("blacklistCount", overall.get("blacklistCount"));
            result.put("rateLimitCount", overall.get("rateLimitCount"));

            long total = ((Number) overall.get("total")).longValue();
            long successCount = ((Number) overall.get("successCount")).longValue();
            double successRate = total > 0 ? (successCount * 100.0 / total) : 0;
            result.put("successRate", String.format("%.2f%%", successRate));
        }

        List<Map<String, Object>> byType = sendRecordMapper.selectStatisticsByType(startTime, endTime);
        result.put("byType", byType);

        List<Map<String, Object>> byChannel = sendRecordMapper.selectStatisticsByChannel(startTime, endTime);
        result.put("byChannel", byChannel);

        return result;
    }

    public List<Map<String, Object>> getTrendStatistics(int days) {
        List<Map<String, Object>> trend = new ArrayList<>();
        LocalDate today = LocalDate.now();

        for (int i = days - 1; i >= 0; i--) {
            LocalDate date = today.minusDays(i);
            LocalDateTime startTime = date.atStartOfDay();
            LocalDateTime endTime = date.atTime(LocalTime.MAX);

            Map<String, Object> dayStats = new HashMap<>();
            dayStats.put("date", date.toString());

            Map<String, Object> stats = sendRecordMapper.selectStatistics(startTime, endTime);
            if (stats != null) {
                dayStats.put("total", stats.get("total"));
                dayStats.put("successCount", stats.get("successCount"));
                dayStats.put("failCount", stats.get("failCount"));
            } else {
                dayStats.put("total", 0);
                dayStats.put("successCount", 0);
                dayStats.put("failCount", 0);
            }

            trend.add(dayStats);
        }

        return trend;
    }
}

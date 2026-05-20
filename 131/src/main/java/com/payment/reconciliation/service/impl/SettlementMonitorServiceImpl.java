package com.payment.reconciliation.service.impl;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.dto.TrendAnalysisDTO;
import com.payment.reconciliation.entity.SettlementMonitor;
import com.payment.reconciliation.enums.SettlementStatusEnum;
import com.payment.reconciliation.mapper.SettlementMonitorMapper;
import com.payment.reconciliation.service.SettlementMonitorService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;

@Slf4j
@Service
public class SettlementMonitorServiceImpl implements SettlementMonitorService {

    @Autowired
    private SettlementMonitorMapper settlementMonitorMapper;

    @Value("${reconciliation.settlement-expected-hours:24}")
    private int settlementExpectedHours;

    @Value("${reconciliation.warning-delay-minutes:120}")
    private int warningDelayMinutes;

    @Value("${reconciliation.serious-delay-minutes:360}")
    private int seriousDelayMinutes;

    @Value("${reconciliation.emergency-delay-minutes:720}")
    private int emergencyDelayMinutes;

    @Override
    @Scheduled(fixedDelay = 600000)
    public void monitorSettlementDelay() {
        log.info("开始检查T+1结算延迟情况");

        LambdaQueryWrapper<SettlementMonitor> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(SettlementMonitor::getStatus,
                SettlementStatusEnum.PENDING.getCode(),
                SettlementStatusEnum.IN_PROGRESS.getCode());

        List<SettlementMonitor> monitors = settlementMonitorMapper.selectList(wrapper);

        for (SettlementMonitor monitor : monitors) {
            checkAndUpdateDelayStatus(monitor);
        }

        log.info("结算延迟检查完成，共检查{}条记录", monitors.size());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void createSettlementMonitor(String channelCode) {
        log.info("创建结算监控记录，渠道: {}", channelCode);

        LocalDate settlementDate = LocalDate.now().minusDays(1);

        LambdaQueryWrapper<SettlementMonitor> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SettlementMonitor::getChannelCode, channelCode)
                .eq(SettlementMonitor::getSettlementDate, settlementDate);

        SettlementMonitor existing = settlementMonitorMapper.selectOne(wrapper);
        if (existing != null) {
            log.info("该渠道今日结算监控记录已存在，channelCode: {}", channelCode);
            return;
        }

        SettlementMonitor monitor = new SettlementMonitor();
        monitor.setMonitorNo(IdUtil.simpleUUID());
        monitor.setChannelCode(channelCode);
        monitor.setSettlementDate(settlementDate);
        monitor.setStatus(SettlementStatusEnum.PENDING.getCode());
        monitor.setExpectedArrivalTime(LocalDateTime.now().plusHours(settlementExpectedHours));
        monitor.setExpectedAmount(BigDecimal.ZERO);
        monitor.setAlertLevel(0);
        monitor.setCreateTime(LocalDateTime.now());
        monitor.setUpdateTime(LocalDateTime.now());

        settlementMonitorMapper.insert(monitor);
        log.info("结算监控记录创建成功，monitorNo: {}", monitor.getMonitorNo());
    }

    private void checkAndUpdateDelayStatus(SettlementMonitor monitor) {
        if (monitor.getActualArrivalTime() != null) {
            return;
        }

        LocalDateTime now = LocalDateTime.now();
        LocalDateTime expectedTime = monitor.getExpectedArrivalTime();

        if (now.isAfter(expectedTime)) {
            long delayMinutes = ChronoUnit.MINUTES.between(expectedTime, now);
            monitor.setDelayMinutes(delayMinutes);

            int alertLevel = 0;
            String alertMessage = "";

            if (delayMinutes >= emergencyDelayMinutes) {
                alertLevel = 3;
                alertMessage = "结算严重延迟，已超过" + emergencyDelayMinutes + "分钟，请立即处理";
            } else if (delayMinutes >= seriousDelayMinutes) {
                alertLevel = 2;
                alertMessage = "结算严重延迟，已超过" + seriousDelayMinutes + "分钟，请关注";
            } else if (delayMinutes >= warningDelayMinutes) {
                alertLevel = 1;
                alertMessage = "结算延迟警告，已超过" + warningDelayMinutes + "分钟";
            }

            if (alertLevel > 0) {
                monitor.setStatus(SettlementStatusEnum.DELAYED.getCode());
                monitor.setAlertLevel(alertLevel);
                monitor.setAlertMessage(alertMessage);
                monitor.setUpdateTime(LocalDateTime.now());
                settlementMonitorMapper.updateById(monitor);

                log.warn("结算延迟告警，monitorNo: {}, 延迟分钟: {}, 告警级别: {}",
                        monitor.getMonitorNo(), delayMinutes, alertLevel);
            }
        }
    }

    @Override
    public List<SettlementMonitor> getDelayedSettlements(Integer alertLevel) {
        return settlementMonitorMapper.selectDelayedSettlements(alertLevel);
    }

    @Override
    public List<SettlementMonitor> getSettlementHistory(TrendAnalysisDTO dto) {
        return settlementMonitorMapper.selectByDateRange(
                dto.getChannelCode(),
                dto.getStartDate(),
                dto.getEndDate()
        );
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void confirmSettlementArrival(Long monitorId) {
        log.info("确认结算到账，monitorId: {}", monitorId);

        SettlementMonitor monitor = settlementMonitorMapper.selectById(monitorId);
        if (monitor == null) {
            throw new RuntimeException("结算监控记录不存在");
        }

        monitor.setActualArrivalTime(LocalDateTime.now());
        monitor.setStatus(SettlementStatusEnum.COMPLETED.getCode());
        monitor.setAlertLevel(0);
        monitor.setAlertMessage("");
        monitor.setUpdateTime(LocalDateTime.now());

        settlementMonitorMapper.updateById(monitor);
        log.info("结算到账确认完成，monitorId: {}", monitorId);
    }
}

package com.dtmonitor.alert.service;

import com.dtmonitor.alert.rule.AlertRule;
import com.dtmonitor.core.enums.AlertLevel;
import com.dtmonitor.core.enums.TransactionStatus;
import com.dtmonitor.core.model.entity.AlertRecord;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.dtmonitor.core.service.AlertRecordService;
import com.dtmonitor.core.service.GlobalTransactionService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
public class AlertEngine {

    private final GlobalTransactionService transactionService;
    private final AlertRecordService alertRecordService;
    private final AlertNotifier alertNotifier;

    private final List<AlertRule> rules = new ArrayList<>();

    public AlertEngine(GlobalTransactionService transactionService,
                       AlertRecordService alertRecordService,
                       AlertNotifier alertNotifier) {
        this.transactionService = transactionService;
        this.alertRecordService = alertRecordService;
        this.alertNotifier = alertNotifier;
    }

    @PostConstruct
    public void initDefaultRules() {
        rules.add(AlertRule.builder()
                .name("Transaction Timeout")
                .description("Transaction exceeded timeout threshold")
                .level(AlertLevel.CRITICAL)
                .condition("TIMEOUT")
                .thresholdMs(30000)
                .enabled(true)
                .build());

        rules.add(AlertRule.builder()
                .name("Transaction Failed")
                .description("Transaction entered failed state")
                .level(AlertLevel.EMERGENCY)
                .condition("STATUS_FAILED")
                .thresholdMs(0)
                .enabled(true)
                .build());

        rules.add(AlertRule.builder()
                .name("Transaction Rollback")
                .description("Transaction was rolled back")
                .level(AlertLevel.WARNING)
                .condition("STATUS_ROLLBACK")
                .thresholdMs(0)
                .enabled(true)
                .build());

        rules.add(AlertRule.builder()
                .name("Long Running Transaction")
                .description("Transaction running beyond expected duration")
                .level(AlertLevel.WARNING)
                .condition("LONG_RUNNING")
                .thresholdMs(60000)
                .enabled(true)
                .build());
    }

    @Scheduled(fixedDelay = 5000)
    public void checkTimeouts() {
        log.debug("Running alert check cycle");
        LocalDateTime threshold = LocalDateTime.now().minusSeconds(30);
        List<GlobalTransaction> candidates = transactionService.findTimeoutCandidates(threshold);

        for (GlobalTransaction tx : candidates) {
            evaluateTransaction(tx);
        }
    }

    public void evaluateTransaction(GlobalTransaction tx) {
        long durationMs = tx.getDurationMs();
        String statusName = tx.getStatus() != null ? tx.getStatus().name() : "UNKNOWN";

        for (AlertRule rule : rules) {
            if (rule.evaluate(durationMs, statusName)) {
                triggerAlert(tx, rule, durationMs);
            }
        }
    }

    private void triggerAlert(GlobalTransaction tx, AlertRule rule, long durationMs) {
        String message = String.format("[%s] Transaction %s: %s (duration=%dms, status=%s)",
                rule.getLevel(), tx.getXid(), rule.getDescription(), durationMs, tx.getStatus());

        AlertRecord record = AlertRecord.builder()
                .alertName(rule.getName())
                .xid(tx.getXid())
                .level(rule.getLevel())
                .alertRule(rule.getCondition())
                .message(message)
                .build();

        alertRecordService.save(record);
        alertNotifier.notify(record);

        log.warn("Alert triggered: {}", message);
    }

    public void addRule(AlertRule rule) {
        rules.add(rule);
    }

    public void removeRule(String ruleName) {
        rules.removeIf(r -> r.getName().equals(ruleName));
    }

    public List<AlertRule> getRules() {
        return new ArrayList<>(rules);
    }

    public void updateTimeoutThreshold(long thresholdMs) {
        rules.stream()
                .filter(r -> "TIMEOUT".equals(r.getCondition()))
                .findFirst()
                .ifPresent(r -> r.setThresholdMs(thresholdMs));
    }
}

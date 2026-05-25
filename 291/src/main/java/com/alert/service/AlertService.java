package com.alert.service;

import com.alert.dto.AlertAcknowledgeRequest;
import com.alert.dto.AlertRequest;
import com.alert.entity.AlertAggregation;
import com.alert.entity.AlertEvent;
import com.alert.entity.AlertHistory;
import com.alert.entity.AlertSuppressionRule;
import com.alert.enums.AlertSeverity;
import com.alert.enums.AlertStatus;
import com.alert.repository.AlertAggregationRepository;
import com.alert.repository.AlertEventRepository;
import com.alert.repository.AlertHistoryRepository;
import com.alert.repository.AlertSuppressionRuleRepository;
import com.alert.util.AggregationFingerprint;
import lombok.extern.slf4j.Slf4j;
import org.kie.api.runtime.KieSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Slf4j
@Service
public class AlertService {

    @Autowired
    private AlertEventRepository alertEventRepository;

    @Autowired
    private AlertAggregationRepository alertAggregationRepository;

    @Autowired
    private AlertHistoryRepository alertHistoryRepository;

    @Autowired
    private AlertSuppressionRuleRepository suppressionRuleRepository;

    @Resource
    private KieSession kieSession;

    @Autowired
    private WebSocketService webSocketService;

    @Value("${alert.escalation.target-severity:CRITICAL}")
    private String targetEscalationSeverity;

    @Value("${alert.escalation.enabled:true}")
    private boolean escalationEnabled;

    @PostConstruct
    public void init() {
        kieSession.setGlobal("alertService", this);
    }

    @Transactional
    public AlertEvent createAlert(AlertRequest request) {
        AlertEvent alert = new AlertEvent();
        alert.setAlertId(UUID.randomUUID().toString().replace("-", ""));
        alert.setTitle(request.getTitle());
        alert.setContent(request.getContent());
        alert.setSeverity(AlertSeverity.valueOf(request.getSeverity()));
        alert.setSource(request.getSource());
        alert.setHost(request.getHost());
        alert.setService(request.getService());
        alert.setTags(request.getTags());
        
        if (request.getAggregationKey() != null && !request.getAggregationKey().isEmpty()) {
            alert.setAggregationKey(request.getAggregationKey());
        } else {
            String fingerprint = AggregationFingerprint.generate(
                    request.getSource(), 
                    request.getHost(), 
                    request.getService(), 
                    request.getTags()
            );
            alert.setAggregationKey(fingerprint);
        }
        
        alert.setParentAlertId(request.getParentAlertId());
        alert.setStatus(AlertStatus.NEW);
        alert.setUpgradeCount(0);

        alert = alertEventRepository.save(alert);
        saveHistory(alert.getAlertId(), "CREATE", "SYSTEM", 
                "告警创建，聚合指纹: " + alert.getAggregationKey());

        checkSuppressionRules(alert);

        kieSession.insert(alert);
        kieSession.fireAllRules();

        webSocketService.broadcastAlert(alert);

        return alert;
    }

    private void checkSuppressionRules(AlertEvent alert) {
        List<AlertSuppressionRule> rules = suppressionRuleRepository.findByEnabledTrue();
        for (AlertSuppressionRule rule : rules) {
            if (matchesSuppressionRule(alert, rule)) {
                alert.setStatus(AlertStatus.SUPPRESSED);
                saveHistory(alert.getAlertId(), "SUPPRESS", "SYSTEM",
                        "被规则抑制: " + rule.getRuleName() + " (依赖: " + rule.getParentCondition() + ")");
                log.info("告警 {} 被抑制规则 {} 抑制", alert.getAlertId(), rule.getRuleName());
                break;
            }
        }
    }

    private boolean matchesSuppressionRule(AlertEvent alert, AlertSuppressionRule rule) {
        boolean childMatch = matchCondition(alert, rule.getChildCondition());
        if (!childMatch) {
            return false;
        }

        List<AlertEvent> activeParentAlerts = alertEventRepository.findByStatusIn(
                Arrays.asList(AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.PROCESSING)
        );

        for (AlertEvent parentAlert : activeParentAlerts) {
            if (matchCondition(parentAlert, rule.getParentCondition())) {
                return true;
            }
        }

        return false;
    }

    private boolean matchCondition(AlertEvent alert, String condition) {
        if (condition == null || condition.isEmpty()) {
            return true;
        }
        String[] parts = condition.split(";");
        for (String part : parts) {
            String[] kv = part.split("=", 2);
            if (kv.length != 2) continue;
            String key = kv[0].trim().toLowerCase();
            String value = kv[1].trim().toLowerCase();
            
            switch (key) {
                case "source":
                    if (alert.getSource() == null || !alert.getSource().toLowerCase().contains(value)) {
                        return false;
                    }
                    break;
                case "host":
                    if (alert.getHost() == null || !alert.getHost().toLowerCase().contains(value)) {
                        return false;
                    }
                    break;
                case "service":
                    if (alert.getService() == null || !alert.getService().toLowerCase().contains(value)) {
                        return false;
                    }
                    break;
                case "severity":
                    if (!alert.getSeverity().getCode().toLowerCase().equals(value)) {
                        return false;
                    }
                    break;
                case "tag":
                    if (alert.getTags() == null || !alert.getTags().toLowerCase().contains(value)) {
                        return false;
                    }
                    break;
                case "title":
                    if (alert.getTitle() == null || !alert.getTitle().toLowerCase().contains(value)) {
                        return false;
                    }
                    break;
            }
        }
        return true;
    }

    @Transactional
    public AlertEvent acknowledgeAlert(String alertId, AlertAcknowledgeRequest request) {
        AlertEvent alert = getAlertById(alertId);
        alert.setStatus(AlertStatus.ACKNOWLEDGED);
        alert.setAssignee(request.getAssignee());
        alert.setAcknowledgeTime(LocalDateTime.now());
        alert = alertEventRepository.save(alert);

        saveHistory(alertId, "ACKNOWLEDGE", request.getAssignee(), request.getRemark());
        webSocketService.broadcastAlert(alert);

        return alert;
    }

    @Transactional
    public AlertEvent processAlert(String alertId, String operator, String remark) {
        AlertEvent alert = getAlertById(alertId);
        alert.setStatus(AlertStatus.PROCESSING);
        alert = alertEventRepository.save(alert);

        saveHistory(alertId, "PROCESS", operator, remark);
        webSocketService.broadcastAlert(alert);

        return alert;
    }

    @Transactional
    public AlertEvent resolveAlert(String alertId, String operator, String remark) {
        AlertEvent alert = getAlertById(alertId);
        alert.setStatus(AlertStatus.RESOLVED);
        alert.setResolveTime(LocalDateTime.now());
        alert = alertEventRepository.save(alert);

        saveHistory(alertId, "RESOLVE", operator, remark);
        webSocketService.broadcastAlert(alert);

        return alert;
    }

    @Transactional
    public AlertEvent closeAlert(String alertId, String operator, String remark) {
        AlertEvent alert = getAlertById(alertId);
        alert.setStatus(AlertStatus.CLOSED);
        alert.setCloseTime(LocalDateTime.now());
        alert = alertEventRepository.save(alert);

        saveHistory(alertId, "CLOSE", operator, remark);
        webSocketService.broadcastAlert(alert);

        return alert;
    }

    @Transactional
    public void aggregateAlert(AlertEvent alert) {
        if (alert.getAggregationKey() == null) {
            return;
        }

        Optional<AlertAggregation> existingAgg = alertAggregationRepository
                .findByAggregationKeyAndStatus(alert.getAggregationKey(), "ACTIVE");

        AlertAggregation aggregation;
        if (existingAgg.isPresent()) {
            aggregation = existingAgg.get();
            aggregation.setCount(aggregation.getCount() + 1);
            aggregation.setLastAlertTime(LocalDateTime.now());
            aggregation.setSeverity(AlertSeverity.getHigherSeverity(aggregation.getSeverity(), alert.getSeverity()));
        } else {
            aggregation = new AlertAggregation();
            aggregation.setAggregationKey(alert.getAggregationKey());
            aggregation.setTitle(alert.getTitle());
            aggregation.setSeverity(alert.getSeverity());
            aggregation.setCount(1);
            aggregation.setStatus("ACTIVE");
            aggregation.setFirstAlertTime(alert.getCreateTime());
            aggregation.setLastAlertTime(alert.getCreateTime());
        }

        alertAggregationRepository.save(aggregation);
        saveHistory(alert.getAlertId(), "AGGREGATE", "SYSTEM",
                "聚合到: " + alert.getAggregationKey() + ", 当前数量: " + aggregation.getCount());

        webSocketService.broadcastAggregation(aggregation);
    }

    @Transactional
    public void suppressAlert(AlertEvent alert) {
        alert.setStatus(AlertStatus.SUPPRESSED);
        alertEventRepository.save(alert);

        saveHistory(alert.getAlertId(), "SUPPRESS", "SYSTEM",
                "被父告警抑制: " + alert.getParentAlertId());

        webSocketService.broadcastAlert(alert);
        log.info("告警 {} 被父告警 {} 抑制", alert.getAlertId(), alert.getParentAlertId());
    }

    @Transactional
    public void scheduleEscalation(AlertEvent alert, int minutes) {
        alert.setNextUpgradeTime(LocalDateTime.now().plusMinutes(minutes));
        alertEventRepository.save(alert);
        log.info("告警 {} 计划在 {} 分钟后升级", alert.getAlertId(), minutes);
    }

    @Scheduled(fixedRate = 60000)
    @Transactional
    public void checkAndEscalateAlerts() {
        List<AlertStatus> activeStatuses = Arrays.asList(AlertStatus.NEW, AlertStatus.ACKNOWLEDGED);
        List<AlertEvent> alertsToEscalate = alertEventRepository
                .findAlertsToEscalate(activeStatuses, LocalDateTime.now());

        for (AlertEvent alert : alertsToEscalate) {
            escalateAlert(alert);
        }
    }

    @Transactional
    public void checkAndEscalate(AlertEvent alert) {
        if (alert.getNextUpgradeTime() != null && LocalDateTime.now().isAfter(alert.getNextUpgradeTime())) {
            escalateAlert(alert);
        }
    }

    private void escalateAlert(AlertEvent alert) {
        if (!escalationEnabled || alert.getUpgradeCount() >= 1) {
            alert.setNextUpgradeTime(null);
            alertEventRepository.save(alert);
            return;
        }

        AlertSeverity currentSeverity = alert.getSeverity();
        AlertSeverity targetSeverity = AlertSeverity.valueOf(targetEscalationSeverity);

        if (currentSeverity == targetSeverity) {
            saveHistory(alert.getAlertId(), "UPGRADE", "SYSTEM",
                    "告警已达到目标级别 " + targetSeverity.getName() + "，停止升级");
            alert.setNextUpgradeTime(null);
            alert.setUpgradeCount(1);
            alertEventRepository.save(alert);
            return;
        }

        alert.setSeverity(targetSeverity);
        alert.setUpgradeCount(1);
        alert.setNextUpgradeTime(null);

        saveHistory(alert.getAlertId(), "UPGRADE", "SYSTEM",
                "单次升级完成，从 " + currentSeverity.getName() + " 直接升级到 " + targetSeverity.getName());

        alertEventRepository.save(alert);
        webSocketService.broadcastAlert(alert);

        log.warn("告警 {} 单次升级完成，从 {} 升级到 {}",
                alert.getAlertId(), currentSeverity.getName(), targetSeverity.getName());
    }

    public AlertEvent getAlertById(String alertId) {
        return alertEventRepository.findByAlertId(alertId)
                .orElseThrow(() -> new RuntimeException("告警不存在: " + alertId));
    }

    public List<AlertEvent> getAllAlerts() {
        return alertEventRepository.findAll();
    }

    public List<AlertHistory> getAlertHistory(String alertId) {
        return alertHistoryRepository.findByAlertIdOrderByCreateTimeDesc(alertId);
    }

    public List<AlertAggregation> getAllAggregations() {
        return alertAggregationRepository.findAll();
    }

    private void saveHistory(String alertId, String operationType, String operator, String remark) {
        AlertHistory history = new AlertHistory();
        history.setAlertId(alertId);
        history.setOperationType(operationType);
        history.setOperator(operator);
        history.setRemark(remark);
        alertHistoryRepository.save(history);
    }
}

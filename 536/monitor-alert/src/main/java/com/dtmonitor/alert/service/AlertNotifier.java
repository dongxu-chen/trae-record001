package com.dtmonitor.alert.service;

import com.dtmonitor.core.model.entity.AlertRecord;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class AlertNotifier {

    private final SimpMessagingTemplate messagingTemplate;

    public AlertNotifier(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void notify(AlertRecord record) {
        try {
            messagingTemplate.convertAndSend("/topic/alerts", record);
            log.info("Alert notification sent via WebSocket: id={}, name={}", record.getId(), record.getAlertName());
        } catch (Exception e) {
            log.error("Failed to send alert notification via WebSocket", e);
        }

        log.info("Alert [{}]: xid={}, level={}, message={}",
                record.getAlertName(), record.getXid(), record.getLevel(), record.getMessage());
    }
}

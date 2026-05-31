package com.datacheck.service;

import com.alibaba.fastjson2.JSON;
import com.datacheck.messagequeue.MessageQueueService;
import com.datacheck.model.CheckResult;
import com.datacheck.model.DiffResult;
import com.datacheck.model.WebSocketMessage;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

@Slf4j
@Service
public class WebSocketService {

    private final SimpMessagingTemplate messagingTemplate;
    private final MessageQueueService messageQueueService;

    @Autowired
    public WebSocketService(SimpMessagingTemplate messagingTemplate,
                            MessageQueueService messageQueueService) {
        this.messagingTemplate = messagingTemplate;
        this.messageQueueService = messageQueueService;
    }

    public void sendDiff(DiffResult diff) {
        WebSocketMessage<DiffResult> message = WebSocketMessage.of("DIFF", diff);
        sendToTopic("/topic/diffs", message);
        messageQueueService.sendDiffToQueue(diff);
    }

    public void sendTaskProgress(String taskId, String status, String message) {
        Map<String, Object> payload = Map.of(
                "taskId", taskId,
                "status", status,
                "message", message
        );
        WebSocketMessage<Map<String, Object>> wsMessage = WebSocketMessage.of("TASK_PROGRESS", payload);
        sendToTopic("/topic/tasks/" + taskId, wsMessage);
    }

    public void sendTaskComplete(String taskId, CheckResult result) {
        WebSocketMessage<CheckResult> message = WebSocketMessage.of("TASK_COMPLETE", result);
        sendToTopic("/topic/tasks/" + taskId, message);
        sendToTopic("/topic/results", message);
        messageQueueService.sendCheckResultToQueue(result);
    }

    public void sendRepairUpdate(DiffResult diff) {
        WebSocketMessage<DiffResult> message = WebSocketMessage.of("REPAIR_UPDATE", diff);
        sendToTopic("/topic/repairs", message);
    }

    public void sendMetrics(Map<String, Object> metrics) {
        WebSocketMessage<Map<String, Object>> message = WebSocketMessage.of("METRICS_UPDATE", metrics);
        sendToTopic("/topic/metrics", message);
    }

    private <T> void sendToTopic(String destination, WebSocketMessage<T> message) {
        try {
            messagingTemplate.convertAndSend(destination, message);
            log.debug("Sent WebSocket message to {}: {}", destination, message.getType());
        } catch (Exception e) {
            log.error("Failed to send WebSocket message to {}", destination, e);
        }
    }
}

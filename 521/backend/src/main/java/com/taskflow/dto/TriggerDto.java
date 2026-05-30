package com.taskflow.dto;

import lombok.Data;

@Data
public class TriggerDto {
    private Long id;
    private Long workflowId;
    private String triggerType;
    private String cronExpression;
    private String eventTopic;
    private String eventFilter;
    private String webhookPath;
    private String webhookSecret;
    private Boolean enabled;

    @Data
    public static class CreateRequest {
        private Long workflowId;
        private String triggerType;
        private String cronExpression;
        private String eventTopic;
        private String eventFilter;
        private String webhookPath;
        private String webhookSecret;
    }
}

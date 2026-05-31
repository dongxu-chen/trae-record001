package com.dlq.platform.common.dto;

import com.dlq.platform.common.enums.AlertLevelEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlertRuleDTO {

    private String id;

    private String name;

    private String description;

    private Boolean enabled;

    private String triggerCondition;

    private AlertLevelEnum alertLevel;

    private String notificationType;

    private String notificationTarget;
}

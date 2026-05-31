package com.dlq.platform.common.entity;

import com.dlq.platform.common.enums.AlertLevelEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlertRule {

    private String id;

    private String name;

    private String description;

    private Boolean enabled;

    private String triggerCondition;

    private AlertLevelEnum alertLevel;

    private String notificationType;

    private String notificationTarget;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}

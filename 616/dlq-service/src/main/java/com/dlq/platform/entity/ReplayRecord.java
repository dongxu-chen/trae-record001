package com.dlq.platform.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReplayRecord {

    private String id;

    private String messageId;

    private String mqType;

    private String targetTopic;

    private String targetQueue;

    private Boolean useOriginalDestination;

    private String operator;

    private String remark;

    private Integer retryCount;

    private Boolean success;

    private String errorMessage;

    private LocalDateTime replayTime;

    private LocalDateTime createTime;

    private String idempotencyKey;
}

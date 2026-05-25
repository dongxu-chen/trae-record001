package com.alert.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

@Data
public class AlertRequest {

    @NotBlank(message = "告警标题不能为空")
    private String title;

    private String content;

    @NotNull(message = "告警级别不能为空")
    private String severity;

    private String source;

    private String host;

    private String service;

    private String tags;

    private String aggregationKey;

    private String parentAlertId;
}

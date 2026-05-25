package com.alert.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;

@Data
public class AlertAcknowledgeRequest {

    @NotBlank(message = "处理人不能为空")
    private String assignee;

    private String remark;
}

package com.pushplatform.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class PushTaskDTO {

    private Long id;

    private Long templateId;

    @NotBlank(message = "推送通道不能为空")
    private String channel;

    private String title;

    @NotBlank(message = "消息内容不能为空")
    private String content;

    private String targetType;

    private List<String> targets;

    private String extParams;

    private LocalDateTime scheduleTime;

    private String remark;
}

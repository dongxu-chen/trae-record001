package com.pushplatform.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;

@Data
public class PushTemplateDTO {

    private Long id;

    @NotBlank(message = "模板编码不能为空")
    private String templateCode;

    @NotBlank(message = "模板名称不能为空")
    private String templateName;

    @NotBlank(message = "推送通道不能为空")
    private String channel;

    private String title;

    @NotBlank(message = "消息内容不能为空")
    private String content;

    private String extParams;

    private Integer status;

    private String remark;
}

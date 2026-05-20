package com.econtract.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;

@Data
public class TemplateDTO {

    @NotBlank(message = "模板名称不能为空")
    private String templateName;

    @NotBlank(message = "模板类型不能为空")
    private String templateType;

    @NotBlank(message = "模板编码不能为空")
    private String templateCode;

    private String fields;

    private String signPositions;
}

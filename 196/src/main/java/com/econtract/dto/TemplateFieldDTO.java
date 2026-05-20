package com.econtract.dto;

import lombok.Data;

@Data
public class TemplateFieldDTO {

    private String fieldName;

    private String fieldLabel;

    private String fieldType;

    private Boolean required;

    private String defaultValue;

    private Integer sort;
}

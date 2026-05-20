package com.pushplatform.dto;

import lombok.Data;

@Data
public class TagCondition {
    private String tagCode;
    private String operator;
    private String tagValue;
    private String logic;
}

package com.dlq.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum ProcessStatusEnum {

    PENDING("PENDING", "待处理"),
    PROCESSED("PROCESSED", "已处理"),
    REPLAYED("REPLAYED", "已重放"),
    ARCHIVED("ARCHIVED", "已归档"),
    IGNORED("IGNORED", "已忽略");

    private final String code;
    private final String desc;
}

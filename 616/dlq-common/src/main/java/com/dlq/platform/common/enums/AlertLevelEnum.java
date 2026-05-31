package com.dlq.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum AlertLevelEnum {

    INFO("INFO", "信息"),
    WARNING("WARNING", "警告"),
    CRITICAL("CRITICAL", "严重");

    private final String code;
    private final String desc;
}

package com.datasecurity.masking.enums;

import lombok.Getter;

@Getter
public enum MaskStrategy {

    MASK("掩码", "用特殊字符替换部分内容"),

    REPLACE("替换", "用固定值替换整个内容"),

    HASH("哈希", "对内容进行哈希运算"),

    TRUNCATE("截断", "只保留部分内容"),

    NONE("不脱敏", "返回原始内容");

    private final String name;

    private final String description;

    MaskStrategy(String name, String description) {
        this.name = name;
        this.description = description;
    }
}

package com.datasecurity.masking.label;

import lombok.Getter;

@Getter
public enum SensitivityLevel {

    PUBLIC(0, "公开", "可公开访问的数据"),
    INTERNAL(1, "内部", "仅内部人员可访问"),
    CONFIDENTIAL(2, "机密", "需授权访问的敏感数据"),
    SECRET(3, "秘密", "高度敏感数据，严格控制访问"),
    TOP_SECRET(4, "绝密", "最高敏感等级，仅限特定人员访问");

    private final int level;
    private final String name;
    private final String description;

    SensitivityLevel(int level, String name, String description) {
        this.level = level;
        this.name = name;
        this.description = description;
    }

    public static SensitivityLevel fromLevel(int level) {
        for (SensitivityLevel sl : values()) {
            if (sl.getLevel() == level) {
                return sl;
            }
        }
        return PUBLIC;
    }

    public boolean isMoreSensitiveThan(SensitivityLevel other) {
        return this.level > other.level;
    }
}

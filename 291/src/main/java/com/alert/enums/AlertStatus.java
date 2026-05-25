package com.alert.enums;

public enum AlertStatus {
    NEW("NEW", "新建"),
    ACKNOWLEDGED("ACKNOWLEDGED", "已认领"),
    PROCESSING("PROCESSING", "处理中"),
    RESOLVED("RESOLVED", "已解决"),
    CLOSED("CLOSED", "已关闭"),
    SUPPRESSED("SUPPRESSED", "已抑制");

    private String code;
    private String name;

    AlertStatus(String code, String name) {
        this.code = code;
        this.name = name;
    }

    public String getCode() {
        return code;
    }

    public String getName() {
        return name;
    }
}

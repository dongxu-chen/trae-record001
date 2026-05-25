package com.alert.enums;

public enum AlertSeverity {
    CRITICAL("CRITICAL", "紧急", 1),
    MAJOR("MAJOR", "重要", 2),
    MINOR("MINOR", "次要", 3),
    WARNING("WARNING", "警告", 4),
    INFO("INFO", "信息", 5);

    private String code;
    private String name;
    private int level;

    AlertSeverity(String code, String name, int level) {
        this.code = code;
        this.name = name;
        this.level = level;
    }

    public String getCode() {
        return code;
    }

    public String getName() {
        return name;
    }

    public int getLevel() {
        return level;
    }

    public static AlertSeverity getHigherSeverity(AlertSeverity s1, AlertSeverity s2) {
        return s1.getLevel() < s2.getLevel() ? s1 : s2;
    }
}

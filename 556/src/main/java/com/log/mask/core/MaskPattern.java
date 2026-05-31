package com.log.mask.core;

public enum MaskPattern {
    PASSWORD("password", "(?i)(password|pwd|passwd|pass)[=:]['\"]?([^'\"\\s,;]+)['\"]?", 2, "******", 100),
    ID_CARD("idCard", "(\\d{6})(19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]", 0, "$1********$6", 90),
    BANK_CARD("bankCard", "\\b(\\d{4})\\d{8,12}(\\d{4})\\b", 0, "$1********$2", 85),
    PHONE("phone", "(1[3-9]\\d)(\\d{4})(\\d{4})", 0, "$1****$3", 80),
    EMAIL("email", "([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})", 0, "***@$2", 70),
    NAME("name", "(姓名|name)[=:]['\"]?([\\u4e00-\\u9fa5]{2,4})['\"]?", 2, "*$2", 60);

    private final String name;
    private final String regex;
    private final int groupIndex;
    private final String replacement;
    private final int priority;

    MaskPattern(String name, String regex, int groupIndex, String replacement, int priority) {
        this.name = name;
        this.regex = regex;
        this.groupIndex = groupIndex;
        this.replacement = replacement;
        this.priority = priority;
    }

    public String getName() {
        return name;
    }

    public String getRegex() {
        return regex;
    }

    public int getGroupIndex() {
        return groupIndex;
    }

    public String getReplacement() {
        return replacement;
    }

    public int getPriority() {
        return priority;
    }
}

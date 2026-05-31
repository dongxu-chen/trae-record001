package com.log.mask.discovery;

public class SensitivePattern {
    private final String name;
    private final String regex;
    private final SensitiveLevel level;
    private final String category;

    public SensitivePattern(String name, String regex, SensitiveLevel level, String category) {
        this.name = name;
        this.regex = regex;
        this.level = level;
        this.category = category;
    }

    public String getName() {
        return name;
    }

    public String getRegex() {
        return regex;
    }

    public SensitiveLevel getLevel() {
        return level;
    }

    public String getCategory() {
        return category;
    }
}

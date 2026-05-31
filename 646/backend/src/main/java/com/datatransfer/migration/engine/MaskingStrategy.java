package com.datatransfer.migration.engine;

public interface MaskingStrategy {
    String mask(String value);
}

class PhoneMaskingStrategy implements MaskingStrategy {
    @Override
    public String mask(String value) {
        if (value == null || value.length() < 7) return value;
        return value.replaceAll("(\\d{3})\\d{4}(\\d{4})", "$1****$2");
    }
}

class EmailMaskingStrategy implements MaskingStrategy {
    @Override
    public String mask(String value) {
        if (value == null || !value.contains("@")) return value;
        int atIndex = value.indexOf('@');
        if (atIndex <= 2) return value;
        return value.charAt(0) + "***" + value.substring(atIndex - 1);
    }
}

class IdCardMaskingStrategy implements MaskingStrategy {
    @Override
    public String mask(String value) {
        if (value == null || value.length() < 10) return value;
        return value.substring(0, 6) + "********" + value.substring(value.length() - 4);
    }
}

class FullMaskingStrategy implements MaskingStrategy {
    @Override
    public String mask(String value) {
        if (value == null) return null;
        return "*".repeat(Math.min(value.length(), 10));
    }
}

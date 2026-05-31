package com.log.mask.dynamic;

public enum MaskPolicy {
    COMPLETE("完全脱敏", 0),
    PARTIAL("部分脱敏", 1),
    FULL("不脱敏", 2);

    private final String label;
    private final int level;

    MaskPolicy(String label, int level) {
        this.label = label;
        this.level = level;
    }

    public String getLabel() { return label; }
    public int getLevel() { return level; }
}

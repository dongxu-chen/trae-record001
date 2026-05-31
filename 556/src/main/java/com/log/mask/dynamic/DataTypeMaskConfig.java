package com.log.mask.dynamic;

public class DataTypeMaskConfig {
    private final String dataType;
    private final String regex;
    private String groupPattern;
    private final String completeReplacement;
    private final String partialReplacement;
    private final String fullReplacement;

    public DataTypeMaskConfig(String dataType, String regex,
                              String completeReplacement, String partialReplacement, String fullReplacement) {
        this.dataType = dataType;
        this.regex = regex;
        this.completeReplacement = completeReplacement;
        this.partialReplacement = partialReplacement;
        this.fullReplacement = fullReplacement;
    }

    public DataTypeMaskConfig withGroupPattern(String groupPattern) {
        this.groupPattern = groupPattern;
        return this;
    }

    public String getDataType() { return dataType; }
    public String getRegex() { return regex; }
    public String getGroupPattern() { return groupPattern; }
    public String getCompleteReplacement() { return completeReplacement; }
    public String getPartialReplacement() { return partialReplacement; }
    public String getFullReplacement() { return fullReplacement; }

    public String getReplacement(MaskPolicy policy) {
        switch (policy) {
            case COMPLETE: return completeReplacement;
            case PARTIAL: return partialReplacement;
            case FULL: return fullReplacement;
            default: return completeReplacement;
        }
    }

    @Override
    public String toString() {
        return "DataTypeMaskConfig{" + dataType + ", complete=" + completeReplacement 
            + ", partial=" + partialReplacement + ", full=" + fullReplacement + "}";
    }
}

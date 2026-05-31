package com.log.mask.core;

public class MaskRule {
    private String name;
    private String regex;
    private int groupIndex;
    private String replacement;
    private boolean enabled;
    private int priority;

    public MaskRule() {
        this.enabled = true;
        this.priority = 0;
    }

    public MaskRule(String name, String regex, int groupIndex, String replacement) {
        this(name, regex, groupIndex, replacement, 0);
    }

    public MaskRule(String name, String regex, int groupIndex, String replacement, int priority) {
        this.name = name;
        this.regex = regex;
        this.groupIndex = groupIndex;
        this.replacement = replacement;
        this.enabled = true;
        this.priority = priority;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getRegex() {
        return regex;
    }

    public void setRegex(String regex) {
        this.regex = regex;
    }

    public int getGroupIndex() {
        return groupIndex;
    }

    public void setGroupIndex(int groupIndex) {
        this.groupIndex = groupIndex;
    }

    public String getReplacement() {
        return replacement;
    }

    public void setReplacement(String replacement) {
        this.replacement = replacement;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public int getPriority() {
        return priority;
    }

    public void setPriority(int priority) {
        this.priority = priority;
    }

    @Override
    public String toString() {
        return "MaskRule{" +
                "name='" + name + '\'' +
                ", regex='" + regex + '\'' +
                ", groupIndex=" + groupIndex +
                ", replacement='" + replacement + '\'' +
                ", enabled=" + enabled +
                ", priority=" + priority +
                '}';
    }
}

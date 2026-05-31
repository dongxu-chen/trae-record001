package com.log.mask.discovery;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class DiscoveryReport {
    private final String source;
    private final int contentLength;
    private final List<SensitiveDataItem> items = new ArrayList<>();
    private boolean finalized = false;
    private long scanTimeMs;
    private int criticalCount;
    private int highCount;
    private int mediumCount;
    private int lowCount;

    public DiscoveryReport(String source, int contentLength) {
        this.source = source;
        this.contentLength = contentLength;
    }

    public void addItem(SensitiveDataItem item) {
        if (!finalized) {
            items.add(item);
        }
    }

    public void finalizeReport() {
        if (finalized) return;
        this.scanTimeMs = System.currentTimeMillis();
        this.criticalCount = countByLevel(SensitiveLevel.CRITICAL);
        this.highCount = countByLevel(SensitiveLevel.HIGH);
        this.mediumCount = countByLevel(SensitiveLevel.MEDIUM);
        this.lowCount = countByLevel(SensitiveLevel.LOW);
        Collections.sort(items, (a, b) -> Integer.compare(b.getLevel().getValue(), a.getLevel().getValue()));
        finalized = true;
    }

    private int countByLevel(SensitiveLevel level) {
        int count = 0;
        for (SensitiveDataItem item : items) {
            if (item.getLevel() == level) count++;
        }
        return count;
    }

    public List<SensitiveDataItem> getItems() {
        return new ArrayList<>(items);
    }

    public List<SensitiveDataItem> getItemsByLevel(SensitiveLevel level) {
        List<SensitiveDataItem> filtered = new ArrayList<>();
        for (SensitiveDataItem item : items) {
            if (item.getLevel() == level) filtered.add(item);
        }
        return filtered;
    }

    public int getTotalCount() {
        return items.size();
    }

    public int getCriticalCount() { return criticalCount; }
    public int getHighCount() { return highCount; }
    public int getMediumCount() { return mediumCount; }
    public int getLowCount() { return lowCount; }

    public boolean hasSensitiveData() {
        return !items.isEmpty();
    }

    public boolean hasCriticalData() {
        return criticalCount > 0;
    }

    public RiskLevel getRiskLevel() {
        if (criticalCount > 0) return RiskLevel.CRITICAL;
        if (highCount > 0) return RiskLevel.HIGH;
        if (mediumCount > 0) return RiskLevel.MEDIUM;
        if (lowCount > 0) return RiskLevel.LOW;
        return RiskLevel.NONE;
    }

    public String toTextReport() {
        StringBuilder sb = new StringBuilder();
        sb.append("╔══════════════════════════════════════════════════╗\n");
        sb.append("║           敏感信息扫描报告                      ║\n");
        sb.append("╠══════════════════════════════════════════════════╣\n");
        sb.append(String.format("║ 数据来源: %-38s ║%n", source.isEmpty() ? "未知" : source));
        sb.append(String.format("║ 数据长度: %-38d ║%n", contentLength));
        sb.append(String.format("║ 风险等级: %-38s ║%n", getRiskLevel().getLabel()));
        sb.append("╠══════════════════════════════════════════════════╣\n");
        sb.append("║ 发现统计:                                       ║\n");
        sb.append(String.format("║   严重: %-4d  高危: %-4d  中危: %-4d  低危: %-4d ║%n", 
            criticalCount, highCount, mediumCount, lowCount));
        sb.append(String.format("║   总计: %-40d ║%n", getTotalCount()));
        sb.append("╠══════════════════════════════════════════════════╣\n");

        if (items.isEmpty()) {
            sb.append("║ 未发现敏感信息                                  ║\n");
        } else {
            sb.append("║ 敏感数据详情:                                   ║\n");
            sb.append("╠══════════════════════════════════════════════════╣\n");
            for (SensitiveDataItem item : items) {
                sb.append(String.format("║ [%s] %s%n", item.getLevel().getLabel(), item.toString()));
            }
        }
        sb.append("╚══════════════════════════════════════════════════╝\n");
        return sb.toString();
    }

    public enum RiskLevel {
        NONE("安全", 0), LOW("低风险", 1), MEDIUM("中风险", 2), HIGH("高风险", 3), CRITICAL("严重风险", 4);

        private final String label;
        private final int value;
        RiskLevel(String label, int value) { this.label = label; this.value = value; }
        public String getLabel() { return label; }
        public int getValue() { return value; }
    }
}

package com.log.mask.audit;

import java.util.Map;

public class AuditStatistics {
    public long totalRecords;
    public Map<String, Integer> dataTypeCounts;
    public Map<MaskAction, Integer> actionCounts;
    public Map<String, Integer> operatorCounts;

    public String toTextReport() {
        StringBuilder sb = new StringBuilder();
        sb.append("╔══════════════════════════════════════════╗\n");
        sb.append("║          脱敏审计统计报告               ║\n");
        sb.append("╠══════════════════════════════════════════╣\n");
        sb.append(String.format("║ 总记录数: %-30d ║%n", totalRecords));
        sb.append("╠══════════════════════════════════════════╣\n");
        sb.append("║ 按数据类型统计:                         ║\n");
        if (dataTypeCounts != null) {
            for (Map.Entry<String, Integer> e : dataTypeCounts.entrySet()) {
                sb.append(String.format("║   %-20s : %-8d ║%n", e.getKey(), e.getValue()));
            }
        }
        sb.append("╠══════════════════════════════════════════╣\n");
        sb.append("║ 按操作类型统计:                         ║\n");
        if (actionCounts != null) {
            for (Map.Entry<MaskAction, Integer> e : actionCounts.entrySet()) {
                sb.append(String.format("║   %-20s : %-8d ║%n", e.getKey().getLabel(), e.getValue()));
            }
        }
        sb.append("╚══════════════════════════════════════════╝\n");
        return sb.toString();
    }
}

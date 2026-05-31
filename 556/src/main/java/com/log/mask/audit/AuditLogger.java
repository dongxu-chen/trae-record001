package com.log.mask.audit;

import java.io.*;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicLong;

public class AuditLogger {
    private static final DateTimeFormatter FORMATTER = 
        DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS");

    private final ConcurrentLinkedQueue<AuditRecord> records = new ConcurrentLinkedQueue<>();
    private final AtomicLong recordCounter = new AtomicLong(0);
    private final int maxRecords;
    private AuditStorage storage;
    private boolean enabled = true;

    public AuditLogger() {
        this(100000);
    }

    public AuditLogger(int maxRecords) {
        this.maxRecords = maxRecords;
    }

    public void setStorage(AuditStorage storage) {
        this.storage = storage;
    }

    public AuditRecord log(AuditRecord record) {
        if (!enabled) return record;
        
        long id = recordCounter.incrementAndGet();
        record.setId(id);
        
        if (records.size() >= maxRecords) {
            records.poll();
        }
        records.offer(record);

        if (storage != null) {
            try {
                storage.store(record);
            } catch (Exception e) {
                // storage failure should not block masking
            }
        }
        return record;
    }

    public AuditRecord logMaskOperation(String operator, String dataType, 
                                         String reason, MaskAction action,
                                         String originalPreview, String maskedPreview,
                                         String source) {
        AuditRecord record = new AuditRecord();
        record.setTimestamp(System.currentTimeMillis());
        record.setOperator(operator);
        record.setDataType(dataType);
        record.setReason(reason);
        record.setAction(action);
        record.setOriginalPreview(originalPreview);
        record.setMaskedPreview(maskedPreview);
        record.setSource(source);
        return log(record);
    }

    public List<AuditRecord> getRecords() {
        return new ArrayList<>(records);
    }

    public List<AuditRecord> getRecordsByOperator(String operator) {
        List<AuditRecord> filtered = new ArrayList<>();
        for (AuditRecord r : records) {
            if (operator.equals(r.getOperator())) filtered.add(r);
        }
        return filtered;
    }

    public List<AuditRecord> getRecordsByDataType(String dataType) {
        List<AuditRecord> filtered = new ArrayList<>();
        for (AuditRecord r : records) {
            if (dataType.equals(r.getDataType())) filtered.add(r);
        }
        return filtered;
    }

    public List<AuditRecord> getRecordsByAction(MaskAction action) {
        List<AuditRecord> filtered = new ArrayList<>();
        for (AuditRecord r : records) {
            if (action == r.getAction()) filtered.add(r);
        }
        return filtered;
    }

    public long getRecordCount() {
        return recordCounter.get();
    }

    public AuditStatistics getStatistics() {
        AuditStatistics stats = new AuditStatistics();
        stats.totalRecords = recordCounter.get();
        
        Map<String, Integer> typeCounts = new HashMap<>();
        Map<MaskAction, Integer> actionCounts = new HashMap<>();
        Map<String, Integer> operatorCounts = new HashMap<>();
        
        for (AuditRecord r : records) {
            typeCounts.merge(r.getDataType(), 1, Integer::sum);
            actionCounts.merge(r.getAction(), 1, Integer::sum);
            operatorCounts.merge(r.getOperator(), 1, Integer::sum);
        }
        
        stats.dataTypeCounts = typeCounts;
        stats.actionCounts = actionCounts;
        stats.operatorCounts = operatorCounts;
        return stats;
    }

    public void clear() {
        records.clear();
    }

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }

    public String exportAsText() {
        StringBuilder sb = new StringBuilder();
        sb.append("时间\t操作人\t数据类型\t操作\t原因\t来源\t原始预览\t脱敏预览\n");
        for (AuditRecord r : records) {
            sb.append(String.format("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",
                formatTime(r.getTimestamp()),
                r.getOperator(),
                r.getDataType(),
                r.getAction().getLabel(),
                r.getReason(),
                r.getSource(),
                r.getOriginalPreview(),
                r.getMaskedPreview()
            ));
        }
        return sb.toString();
    }

    public void exportToFile(String filePath) throws IOException {
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(filePath))) {
            writer.write(exportAsText());
        }
    }

    private String formatTime(long timestamp) {
        return LocalDateTime.ofInstant(Instant.ofEpochMilli(timestamp), ZoneId.systemDefault())
            .format(FORMATTER);
    }
}

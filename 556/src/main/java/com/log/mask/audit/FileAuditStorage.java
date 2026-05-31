package com.log.mask.audit;

import java.io.*;

public class FileAuditStorage implements AuditStorage {
    private final String filePath;
    private final Object lock = new Object();

    public FileAuditStorage(String filePath) {
        this.filePath = filePath;
    }

    @Override
    public void store(AuditRecord record) throws Exception {
        synchronized (lock) {
            try (BufferedWriter writer = new BufferedWriter(new FileWriter(filePath, true))) {
                writer.write(formatRecord(record));
                writer.newLine();
                writer.flush();
            }
        }
    }

    private String formatRecord(AuditRecord r) {
        return String.format("%d|%d|%s|%s|%s|%s|%s|%s|%s",
            r.getId(),
            r.getTimestamp(),
            r.getOperator(),
            r.getDataType(),
            r.getAction().getLabel(),
            r.getReason(),
            r.getSource() != null ? r.getSource() : "",
            r.getOriginalPreview() != null ? r.getOriginalPreview() : "",
            r.getMaskedPreview() != null ? r.getMaskedPreview() : ""
        );
    }
}

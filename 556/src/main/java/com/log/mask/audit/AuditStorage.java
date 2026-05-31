package com.log.mask.audit;

public interface AuditStorage {
    void store(AuditRecord record) throws Exception;
}

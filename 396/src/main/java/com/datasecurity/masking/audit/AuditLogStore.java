package com.datasecurity.masking.audit;

import java.util.List;

public interface AuditLogStore {

    void save(AuditLog auditLog);

    List<AuditLog> findByUserId(String userId, long startTime, long endTime);

    List<AuditLog> findByDatabaseId(String databaseId, long startTime, long endTime);

    List<AuditLog> findByTableName(String tableName, long startTime, long endTime);

    List<AuditLog> findBySensitiveType(String sensitiveType, long startTime, long endTime);

    List<AuditLog> findByOperation(String operation, long startTime, long endTime);

    List<AuditLog> findAll(long startTime, long endTime, int page, int size);

    long count(long startTime, long endTime);
}

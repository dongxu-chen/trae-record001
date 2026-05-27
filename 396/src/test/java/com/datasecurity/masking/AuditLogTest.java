package com.datasecurity.masking;

import com.datasecurity.masking.audit.AuditLog;
import com.datasecurity.masking.audit.AuditLogStore;
import com.datasecurity.masking.audit.InMemoryAuditLogStore;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class AuditLogTest {

    private AuditLogStore auditLogStore;

    @BeforeEach
    void setUp() {
        auditLogStore = new InMemoryAuditLogStore();
    }

    @Test
    void testSaveAuditLog() {
        AuditLog log = AuditLog.builder()
                .userId("user123")
                .username("testuser")
                .userRole("VIEWER")
                .operation("QUERY")
                .databaseId("default")
                .tableName("users")
                .sensitiveColumns(List.of("phone", "id_card"))
                .sensitiveTypes(List.of("PHONE", "ID_CARD"))
                .sql("SELECT * FROM users WHERE id = 1")
                .rowCount(1)
                .clientIp("192.168.1.100")
                .build();

        auditLogStore.save(log);

        assertNotNull(log.getId());
        assertNotNull(log.getTimestamp());
    }

    @Test
    void testFindByUserId() {
        long now = System.currentTimeMillis();

        AuditLog log1 = AuditLog.builder()
                .userId("user001")
                .operation("QUERY")
                .build();
        auditLogStore.save(log1);

        AuditLog log2 = AuditLog.builder()
                .userId("user001")
                .operation("EXPORT")
                .build();
        auditLogStore.save(log2);

        AuditLog log3 = AuditLog.builder()
                .userId("user002")
                .operation("QUERY")
                .build();
        auditLogStore.save(log3);

        List<AuditLog> results = auditLogStore.findByUserId("user001", 0, now + 1000);
        assertEquals(2, results.size());
    }

    @Test
    void testFindByDatabaseId() {
        long now = System.currentTimeMillis();

        AuditLog log1 = AuditLog.builder()
                .userId("user001")
                .databaseId("mysql_prod")
                .build();
        auditLogStore.save(log1);

        AuditLog log2 = AuditLog.builder()
                .userId("user002")
                .databaseId("mysql_prod")
                .build();
        auditLogStore.save(log2);

        List<AuditLog> results = auditLogStore.findByDatabaseId("mysql_prod", 0, now + 1000);
        assertEquals(2, results.size());
    }

    @Test
    void testFindByTableName() {
        long now = System.currentTimeMillis();

        AuditLog log1 = AuditLog.builder()
                .tableName("users")
                .build();
        auditLogStore.save(log1);

        AuditLog log2 = AuditLog.builder()
                .tableName("orders")
                .build();
        auditLogStore.save(log2);

        List<AuditLog> results = auditLogStore.findByTableName("users", 0, now + 1000);
        assertEquals(1, results.size());
        assertEquals("users", results.get(0).getTableName());
    }

    @Test
    void testFindBySensitiveType() {
        long now = System.currentTimeMillis();

        AuditLog log1 = AuditLog.builder()
                .sensitiveTypes(List.of("PHONE", "NAME"))
                .build();
        auditLogStore.save(log1);

        AuditLog log2 = AuditLog.builder()
                .sensitiveTypes(List.of("ID_CARD", "BANK_CARD"))
                .build();
        auditLogStore.save(log2);

        AuditLog log3 = AuditLog.builder()
                .sensitiveTypes(List.of("PHONE"))
                .build();
        auditLogStore.save(log3);

        List<AuditLog> results = auditLogStore.findBySensitiveType("PHONE", 0, now + 1000);
        assertEquals(2, results.size());
    }

    @Test
    void testFindByOperation() {
        long now = System.currentTimeMillis();

        for (int i = 0; i < 5; i++) {
            auditLogStore.save(AuditLog.builder().operation("QUERY").build());
        }
        for (int i = 0; i < 3; i++) {
            auditLogStore.save(AuditLog.builder().operation("EXPORT").build());
        }

        assertEquals(5, auditLogStore.findByOperation("QUERY", 0, now + 1000).size());
        assertEquals(3, auditLogStore.findByOperation("EXPORT", 0, now + 1000).size());
    }

    @Test
    void testFindAllWithPagination() {
        long now = System.currentTimeMillis();

        for (int i = 0; i < 25; i++) {
            auditLogStore.save(AuditLog.builder()
                    .userId("user_" + i)
                    .build());
        }

        List<AuditLog> page1 = auditLogStore.findAll(0, now + 1000, 0, 10);
        assertEquals(10, page1.size());

        List<AuditLog> page2 = auditLogStore.findAll(0, now + 1000, 1, 10);
        assertEquals(10, page2.size());

        List<AuditLog> page3 = auditLogStore.findAll(0, now + 1000, 2, 10);
        assertEquals(5, page3.size());
    }

    @Test
    void testCount() {
        long now = System.currentTimeMillis();

        for (int i = 0; i < 10; i++) {
            auditLogStore.save(AuditLog.builder().build());
        }

        assertEquals(10, auditLogStore.count(0, now + 1000));
    }

    @Test
    void testTimeRangeFilter() {
        long now = System.currentTimeMillis();
        long oneHourAgo = now - 3600000;
        long oneHourLater = now + 3600000;

        AuditLog log1 = AuditLog.builder().userId("old").build();
        log1.setTimestamp(oneHourAgo);
        auditLogStore.save(log1);

        AuditLog log2 = AuditLog.builder().userId("new").build();
        auditLogStore.save(log2);

        List<AuditLog> recentLogs = auditLogStore.findByUserId("new", now - 1000, oneHourLater);
        assertEquals(1, recentLogs.size());
    }

    @Test
    void testClearAll() {
        for (int i = 0; i < 5; i++) {
            auditLogStore.save(AuditLog.builder().build());
        }

        assertEquals(5, auditLogStore.count(0, System.currentTimeMillis() + 1000));

        ((InMemoryAuditLogStore) auditLogStore).clearAll();

        assertEquals(0, auditLogStore.count(0, System.currentTimeMillis() + 1000));
    }

    @Test
    void testMaxLogSize() {
        for (int i = 0; i < 100001; i++) {
            auditLogStore.save(AuditLog.builder().userId("user_" + i).build());
        }

        assertTrue(auditLogStore.count(0, System.currentTimeMillis() + 1000) <= 100000);
    }
}

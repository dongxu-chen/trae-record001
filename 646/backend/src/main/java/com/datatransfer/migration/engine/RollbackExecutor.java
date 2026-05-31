package com.datatransfer.migration.engine;

import com.datatransfer.migration.adapter.DataSourceAdapter;
import com.datatransfer.migration.model.RollbackRecord;
import com.datatransfer.migration.repository.RollbackRecordRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class RollbackExecutor {
    private final RollbackRecordRepository rollbackRecordRepository;
    private final Map<Long, RollbackRecord> runningRollbacks = new ConcurrentHashMap<>();

    public RollbackExecutor(RollbackRecordRepository rollbackRecordRepository) {
        this.rollbackRecordRepository = rollbackRecordRepository;
    }

    public RollbackRecord createBackup(Long taskId, DataSourceAdapter targetAdapter,
                                       String targetTableName, String rollbackStrategy) throws Exception {
        String backupTableName = generateBackupTableName(targetTableName);
        RollbackRecord record = new RollbackRecord();
        record.setTaskId(taskId);
        record.setTableName(targetTableName);
        record.setBackupTableName(backupTableName);
        record.setRollbackStrategy(rollbackStrategy);
        record.setRollbackStatus("BACKING_UP");
        record.setCreatedAt(LocalDateTime.now());
        record.setUpdatedAt(LocalDateTime.now());
        rollbackRecordRepository.insert(record);

        try {
            long backupCount = performBackup(targetAdapter, targetTableName, backupTableName);
            record.setBackupRecords(backupCount);
            record.setRollbackStatus("BACKUP_COMPLETED");
            record.setUpdatedAt(LocalDateTime.now());
            rollbackRecordRepository.updateById(record);
            log.info("Backup created successfully for task {}: {} records backed up to {}",
                    taskId, backupCount, backupTableName);
        } catch (Exception e) {
            record.setRollbackStatus("BACKUP_FAILED");
            record.setErrorMessage(e.getMessage());
            record.setUpdatedAt(LocalDateTime.now());
            rollbackRecordRepository.updateById(record);
            log.error("Backup failed for task {}", taskId, e);
            throw e;
        }

        return record;
    }

    @Async
    public void executeRollback(Long taskId, DataSourceAdapter targetAdapter, RollbackRecord backupRecord) {
        log.info("Starting rollback for task {}, strategy: {}", taskId, backupRecord.getRollbackStrategy());
        runningRollbacks.put(taskId, backupRecord);

        try {
            backupRecord.setRollbackStatus("ROLLING_BACK");
            backupRecord.setUpdatedAt(LocalDateTime.now());
            rollbackRecordRepository.updateById(backupRecord);

            performRollback(targetAdapter, backupRecord);

            backupRecord.setRollbackStatus("ROLLBACK_COMPLETED");
            backupRecord.setUpdatedAt(LocalDateTime.now());
            rollbackRecordRepository.updateById(backupRecord);
            log.info("Rollback completed successfully for task {}", taskId);
        } catch (Exception e) {
            backupRecord.setRollbackStatus("ROLLBACK_FAILED");
            backupRecord.setErrorMessage(e.getMessage());
            backupRecord.setUpdatedAt(LocalDateTime.now());
            rollbackRecordRepository.updateById(backupRecord);
            log.error("Rollback failed for task {}", taskId, e);
        } finally {
            runningRollbacks.remove(taskId);
        }
    }

    public RollbackRecord getLatestRollbackRecord(Long taskId) {
        return rollbackRecordRepository.selectOne(
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<RollbackRecord>()
                        .eq(RollbackRecord::getTaskId, taskId)
                        .orderByDesc(RollbackRecord::getUpdatedAt)
                        .last("LIMIT 1")
        );
    }

    public Map<String, Object> getRollbackStatus(Long taskId) {
        Map<String, Object> result = new java.util.HashMap<>();
        RollbackRecord record = runningRollbacks.get(taskId);
        if (record == null) {
            record = getLatestRollbackRecord(taskId);
        }
        if (record != null) {
            result.put("success", true);
            result.put("taskId", taskId);
            result.put("rollbackStatus", record.getRollbackStatus());
            result.put("backupTableName", record.getBackupTableName());
            result.put("backupRecords", record.getBackupRecords());
            result.put("rollbackStrategy", record.getRollbackStrategy());
            result.put("errorMessage", record.getErrorMessage());
            result.put("updatedAt", record.getUpdatedAt());
        } else {
            result.put("success", false);
            result.put("message", "No rollback record found");
        }
        return result;
    }

    public boolean isRollbackRunning(Long taskId) {
        return runningRollbacks.containsKey(taskId);
    }

    private long performBackup(DataSourceAdapter adapter, String sourceTable, String backupTable) throws Exception {
        java.sql.Connection conn = null;
        try {
            conn = getConnectionFromAdapter(adapter);
            try (Statement stmt = conn.createStatement()) {
                String dropSql = String.format("DROP TABLE IF EXISTS %s", backupTable);
                stmt.execute(dropSql);

                String createSql = String.format("CREATE TABLE %s LIKE %s", backupTable, sourceTable);
                stmt.execute(createSql);

                String insertSql = String.format("INSERT INTO %s SELECT * FROM %s", backupTable, sourceTable);
                stmt.execute(insertSql);

                String countSql = String.format("SELECT COUNT(*) FROM %s", backupTable);
                try (ResultSet rs = stmt.executeQuery(countSql)) {
                    if (rs.next()) {
                        return rs.getLong(1);
                    }
                }
            }
        } finally {
            if (conn != null) {
                try { conn.setAutoCommit(true); } catch (Exception e) { /* ignore */ }
            }
        }
        return 0;
    }

    private void performRollback(DataSourceAdapter adapter, RollbackRecord record) throws Exception {
        String strategy = record.getRollbackStrategy();
        String targetTable = record.getTableName();
        String backupTable = record.getBackupTableName();

        switch (strategy != null ? strategy : "table_restore") {
            case "table_restore":
                performTableRestore(adapter, targetTable, backupTable);
                break;
            case "truncate_and_restore":
                performTruncateAndRestore(adapter, targetTable, backupTable);
                break;
            default:
                performTableRestore(adapter, targetTable, backupTable);
        }
    }

    private void performTableRestore(DataSourceAdapter adapter, String targetTable, String backupTable) throws Exception {
        Connection conn = null;
        try {
            conn = getConnectionFromAdapter(adapter);
            conn.setAutoCommit(false);
            try (Statement stmt = conn.createStatement()) {
                String truncateSql = String.format("TRUNCATE TABLE %s", targetTable);
                stmt.execute(truncateSql);

                String insertSql = String.format("INSERT INTO %s SELECT * FROM %s", targetTable, backupTable);
                stmt.execute(insertSql);

                conn.commit();
                log.info("Table restore completed: {} restored from {}", targetTable, backupTable);
            }
        } catch (Exception e) {
            if (conn != null) {
                try { conn.rollback(); } catch (Exception ex) { log.error("Rollback of restore failed", ex); }
            }
            throw e;
        } finally {
            if (conn != null) {
                conn.setAutoCommit(true);
            }
        }
    }

    private void performTruncateAndRestore(DataSourceAdapter adapter, String targetTable, String backupTable) throws Exception {
        performTableRestore(adapter, targetTable, backupTable);
    }

    private String generateBackupTableName(String originalName) {
        String timestamp = java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss").format(LocalDateTime.now());
        return String.format("%s_bak_%s", originalName, timestamp);
    }

    private java.sql.Connection getConnectionFromAdapter(DataSourceAdapter adapter) throws Exception {
        if (adapter instanceof com.datatransfer.migration.adapter.MysqlDataSourceAdapter) {
            java.lang.reflect.Field field = com.datatransfer.migration.adapter.MysqlDataSourceAdapter.class.getDeclaredField("connection");
            field.setAccessible(true);
            java.sql.Connection conn = (java.sql.Connection) field.get(adapter);
            if (conn == null || conn.isClosed()) {
                java.lang.reflect.Method method = com.datatransfer.migration.adapter.MysqlDataSourceAdapter.class.getDeclaredMethod("getConnection");
                method.setAccessible(true);
                conn = (java.sql.Connection) method.invoke(adapter);
            }
            return conn;
        }
        throw new UnsupportedOperationException("Rollback not supported for this adapter type: " + adapter.getClass().getSimpleName());
    }
}

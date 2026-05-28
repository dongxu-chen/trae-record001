package com.datasync.writer.postgresql;

import com.datasync.common.model.ColumnMetaData;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.RowData;
import com.datasync.common.model.SyncResult;
import com.datasync.writer.AbstractDatabaseWriter;
import lombok.extern.slf4j.Slf4j;

import javax.sql.DataSource;
import java.sql.Connection;
import java.util.List;
import java.util.Map;

@Slf4j
public class PostgreSQLWriter extends AbstractDatabaseWriter {
    public PostgreSQLWriter(DataSource dataSource, String databaseId, String datacenterId) {
        super(dataSource, databaseId, datacenterId);
    }

    @Override
    protected String getUpsertSql(String tableName, Map<String, ColumnMetaData> columns, List<String> primaryKeys) {
        String colList = buildColumnList(columns);
        String placeholders = buildPlaceholders(columns);
        StringBuilder updateSets = new StringBuilder();
        boolean first = true;
        for (String colName : columns.keySet()) {
            if (primaryKeys.contains(colName)) {
                continue;
            }
            if (!first) {
                updateSets.append(", ");
            }
            updateSets.append(colName).append(" = EXCLUDED.").append(colName);
            first = false;
        }

        String conflictTarget = String.join(", ", primaryKeys);

        return String.format("INSERT INTO %s (%s) VALUES (%s) ON CONFLICT (%s) DO UPDATE SET %s",
                tableName, colList, placeholders, conflictTarget, updateSets);
    }

    @Override
    protected String getInsertSql(String tableName, Map<String, ColumnMetaData> columns) {
        String colList = buildColumnList(columns);
        String placeholders = buildPlaceholders(columns);
        return String.format("INSERT INTO %s (%s) VALUES (%s)", tableName, colList, placeholders);
    }

    @Override
    protected String getUpdateSql(String tableName, Map<String, ColumnMetaData> columns, List<String> primaryKeys) {
        String updateSets = buildUpdateSets(columns, primaryKeys);
        String whereClause = buildWhereClause(primaryKeys);
        return String.format("UPDATE %s SET %s WHERE %s", tableName, updateSets, whereClause);
    }

    @Override
    protected String getDeleteSql(String tableName, List<String> primaryKeys) {
        String whereClause = buildWhereClause(primaryKeys);
        return String.format("DELETE FROM %s WHERE %s", tableName, whereClause);
    }

    @Override
    public SyncResult write(DataChangeEvent event) {
        long startTime = System.currentTimeMillis();
        try (Connection conn = dataSource.getConnection()) {
            conn.setAutoCommit(false);

            for (RowData rowData : event.getRowDataList()) {
                switch (event.getOperationType()) {
                    case INSERT:
                        executeInsert(conn, event, rowData);
                        break;
                    case UPDATE:
                        executeUpsert(conn, event, rowData);
                        break;
                    case DELETE:
                        executeDelete(conn, event, rowData);
                        break;
                    default:
                        log.warn("Unsupported operation type: {}", event.getOperationType());
                }
            }

            conn.commit();
            long processTime = System.currentTimeMillis() - startTime;
            log.debug("Successfully wrote event to PostgreSQL: eventId={}, table={}, operation={}, rows={}",
                    event.getEventId(), event.getFullTableName(), event.getOperationType(), event.getRowDataList().size());
            return SyncResult.success(event.getEventId(), processTime);
        } catch (Exception e) {
            log.error("Failed to write event to PostgreSQL: eventId={}, table={}, error={}",
                    event.getEventId(), event.getFullTableName(), e.getMessage(), e);
            return SyncResult.failure(event.getEventId(), e.getMessage(), e);
        }
    }
}

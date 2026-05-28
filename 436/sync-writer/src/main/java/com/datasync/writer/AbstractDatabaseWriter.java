package com.datasync.writer;

import com.datasync.common.enums.OperationType;
import com.datasync.common.model.ColumnMetaData;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.RowData;
import com.datasync.common.model.SyncResult;
import lombok.extern.slf4j.Slf4j;

import javax.sql.DataSource;
import java.sql.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
public abstract class AbstractDatabaseWriter implements DatabaseWriter {
    protected final DataSource dataSource;
    protected final String databaseId;
    protected final String datacenterId;

    protected AbstractDatabaseWriter(DataSource dataSource, String databaseId, String datacenterId) {
        this.dataSource = dataSource;
        this.databaseId = databaseId;
        this.datacenterId = datacenterId;
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
                        executeUpdate(conn, event, rowData);
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
            log.debug("Successfully wrote event: eventId={}, table={}, operation={}, rows={}",
                    event.getEventId(), event.getFullTableName(), event.getOperationType(), event.getRowDataList().size());
            return SyncResult.success(event.getEventId(), processTime);
        } catch (Exception e) {
            log.error("Failed to write event: eventId={}, table={}, error={}",
                    event.getEventId(), event.getFullTableName(), e.getMessage(), e);
            return SyncResult.failure(event.getEventId(), e.getMessage(), e);
        }
    }

    @Override
    public List<SyncResult> writeBatch(List<DataChangeEvent> events) {
        List<SyncResult> results = new ArrayList<>();
        for (DataChangeEvent event : events) {
            results.add(write(event));
        }
        return results;
    }

    @Override
    public boolean isHealthy() {
        try (Connection conn = dataSource.getConnection()) {
            return conn.isValid(5);
        } catch (Exception e) {
            log.error("Health check failed for database: {}", databaseId, e);
            return false;
        }
    }

    @Override
    public void shutdown() {
        log.info("Shutting down database writer: {}", databaseId);
    }

    protected abstract String getUpsertSql(String tableName, Map<String, ColumnMetaData> columns, List<String> primaryKeys);

    protected abstract String getInsertSql(String tableName, Map<String, ColumnMetaData> columns);

    protected abstract String getUpdateSql(String tableName, Map<String, ColumnMetaData> columns, List<String> primaryKeys);

    protected abstract String getDeleteSql(String tableName, List<String> primaryKeys);

    protected void executeInsert(Connection conn, DataChangeEvent event, RowData rowData) throws SQLException {
        String sql = getInsertSql(event.getFullTableName(), event.getColumnMetaData());
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            setParameters(ps, event.getColumnMetaData(), rowData.getAfterColumns(), event.getColumnMetaData().values());
            ps.executeUpdate();
        }
    }

    protected void executeUpsert(Connection conn, DataChangeEvent event, RowData rowData) throws SQLException {
        String sql = getUpsertSql(event.getFullTableName(), event.getColumnMetaData(), event.getPrimaryKeys());
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            Map<String, Object> values = rowData.getAfterColumns();
            List<ColumnMetaData> columns = new ArrayList<>(event.getColumnMetaData().values());
            setParameters(ps, event.getColumnMetaData(), values, columns);
            ps.executeUpdate();
        }
    }

    protected void executeUpdate(Connection conn, DataChangeEvent event, RowData rowData) throws SQLException {
        String sql = getUpdateSql(event.getFullTableName(), event.getColumnMetaData(), event.getPrimaryKeys());
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            int paramIndex = 1;
            for (Map.Entry<String, ColumnMetaData> entry : event.getColumnMetaData().entrySet()) {
                if (event.getPrimaryKeys().contains(entry.getKey())) {
                    continue;
                }
                Object value = rowData.getAfterValue(entry.getKey());
                setParameter(ps, paramIndex++, value, entry.getValue());
            }
            for (String pk : event.getPrimaryKeys()) {
                Object value = rowData.getBeforeValue(pk);
                if (value == null) {
                    value = rowData.getAfterValue(pk);
                }
                ColumnMetaData meta = event.getColumnMetaData().get(pk);
                setParameter(ps, paramIndex++, value, meta);
            }
            ps.executeUpdate();
        }
    }

    protected void executeDelete(Connection conn, DataChangeEvent event, RowData rowData) throws SQLException {
        String sql = getDeleteSql(event.getFullTableName(), event.getPrimaryKeys());
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            int paramIndex = 1;
            for (String pk : event.getPrimaryKeys()) {
                Object value = rowData.getBeforeValue(pk);
                if (value == null) {
                    value = rowData.getAfterValue(pk);
                }
                ColumnMetaData meta = event.getColumnMetaData().get(pk);
                setParameter(ps, paramIndex++, value, meta);
            }
            ps.executeUpdate();
        }
    }

    protected void setParameters(PreparedStatement ps,
                                  Map<String, ColumnMetaData> columnMetaData,
                                  Map<String, Object> values,
                                  List<ColumnMetaData> columns) throws SQLException {
        int paramIndex = 1;
        for (ColumnMetaData meta : columns) {
            Object value = values.get(meta.getColumnName());
            setParameter(ps, paramIndex++, value, meta);
        }
    }

    protected void setParameter(PreparedStatement ps, int paramIndex, Object value, ColumnMetaData meta) throws SQLException {
        if (value == null) {
            ps.setObject(paramIndex, null);
            return;
        }

        int sqlType = meta.getColumnType();
        if (value instanceof String) {
            ps.setString(paramIndex, (String) value);
        } else if (value instanceof Integer) {
            ps.setInt(paramIndex, (Integer) value);
        } else if (value instanceof Long) {
            ps.setLong(paramIndex, (Long) value);
        } else if (value instanceof Double) {
            ps.setDouble(paramIndex, (Double) value);
        } else if (value instanceof Float) {
            ps.setFloat(paramIndex, (Float) value);
        } else if (value instanceof Boolean) {
            ps.setBoolean(paramIndex, (Boolean) value);
        } else if (value instanceof LocalDateTime) {
            ps.setTimestamp(paramIndex, Timestamp.valueOf((LocalDateTime) value));
        } else if (value instanceof LocalDate) {
            ps.setDate(paramIndex, Date.valueOf((LocalDate) value));
        } else if (value instanceof LocalTime) {
            ps.setTime(paramIndex, Time.valueOf((LocalTime) value));
        } else if (value instanceof byte[]) {
            ps.setBytes(paramIndex, (byte[]) value);
        } else if (value instanceof java.math.BigDecimal) {
            ps.setBigDecimal(paramIndex, (java.math.BigDecimal) value);
        } else {
            ps.setObject(paramIndex, value, sqlType);
        }
    }

    protected String buildColumnList(Map<String, ColumnMetaData> columns) {
        return String.join(", ", columns.keySet());
    }

    protected String buildPlaceholders(Map<String, ColumnMetaData> columns) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < columns.size(); i++) {
            if (i > 0) {
                sb.append(", ");
            }
            sb.append("?");
        }
        return sb.toString();
    }

    protected String buildUpdateSets(Map<String, ColumnMetaData> columns, List<String> primaryKeys) {
        StringBuilder sb = new StringBuilder();
        boolean first = true;
        for (String colName : columns.keySet()) {
            if (primaryKeys.contains(colName)) {
                continue;
            }
            if (!first) {
                sb.append(", ");
            }
            sb.append(colName).append(" = ?");
            first = false;
        }
        return sb.toString();
    }

    protected String buildWhereClause(List<String> primaryKeys) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < primaryKeys.size(); i++) {
            if (i > 0) {
                sb.append(" AND ");
            }
            sb.append(primaryKeys.get(i)).append(" = ?");
        }
        return sb.toString();
    }

    protected String quoteIdentifier(String identifier) {
        return "\"" + identifier + "\"";
    }
}

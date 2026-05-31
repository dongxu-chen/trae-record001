package com.datacheck.datasource;

import com.datacheck.model.CheckTask;
import com.datacheck.model.DataRecord;
import com.datacheck.model.enums.DataSourceType;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Component
public class MysqlDataSourceAdapter implements DataSourceAdapter {

    private final JdbcTemplate sourceJdbcTemplate;
    private final JdbcTemplate targetJdbcTemplate;
    private final Cache<String, List<String>> columnCache;

    @Autowired
    public MysqlDataSourceAdapter(
            @Qualifier("sourceMysqlDataSource") DataSource sourceDataSource,
            @Qualifier("targetMysqlDataSource") DataSource targetDataSource) {
        this.sourceJdbcTemplate = new JdbcTemplate(sourceDataSource);
        this.targetJdbcTemplate = new JdbcTemplate(targetDataSource);
        this.columnCache = Caffeine.newBuilder()
                .expireAfterWrite(10, TimeUnit.MINUTES)
                .maximumSize(1000)
                .build();
    }

    @Override
    public DataSourceType getType() {
        return DataSourceType.MYSQL;
    }

    @Override
    public Iterator<DataRecord> iterateSource(CheckTask task) {
        return new MysqlRecordIterator(sourceJdbcTemplate, task);
    }

    @Override
    public Iterator<DataRecord> iterateTarget(CheckTask task) {
        return new MysqlRecordIterator(targetJdbcTemplate, task);
    }

    @Override
    public DataRecord getSourceRecord(String key, CheckTask task) {
        return getRecord(sourceJdbcTemplate, key, task);
    }

    @Override
    public DataRecord getTargetRecord(String key, CheckTask task) {
        return getRecord(targetJdbcTemplate, key, task);
    }

    @Override
    public long getSourceCount(CheckTask task) {
        return getCount(sourceJdbcTemplate, task);
    }

    @Override
    public long getTargetCount(CheckTask task) {
        return getCount(targetJdbcTemplate, task);
    }

    @Override
    public boolean insertTarget(DataRecord record, CheckTask task) {
        return executeInsert(targetJdbcTemplate, record, task);
    }

    @Override
    public boolean updateTarget(DataRecord record, CheckTask task) {
        return executeUpdate(targetJdbcTemplate, record, task);
    }

    @Override
    public boolean deleteTarget(String key, CheckTask task) {
        return executeDelete(targetJdbcTemplate, key, task);
    }

    @Override
    public List<String> getPrimaryKeys(String tableName) {
        String cacheKey = "pk:" + tableName;
        return columnCache.get(cacheKey, k -> {
            String sql = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE " +
                    "WHERE TABLE_NAME = ? AND CONSTRAINT_NAME = 'PRIMARY' " +
                    "ORDER BY ORDINAL_POSITION";
            try {
                return sourceJdbcTemplate.queryForList(sql, String.class, tableName);
            } catch (DataAccessException e) {
                log.error("Failed to get primary keys for table: {}", tableName, e);
                return Collections.emptyList();
            }
        });
    }

    @Override
    public List<String> getColumns(String tableName) {
        String cacheKey = "cols:" + tableName;
        return columnCache.get(cacheKey, k -> {
            String sql = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS " +
                    "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION";
            try {
                return sourceJdbcTemplate.queryForList(sql, String.class, tableName);
            } catch (DataAccessException e) {
                log.error("Failed to get columns for table: {}", tableName, e);
                return Collections.emptyList();
            }
        });
    }

    private DataRecord getRecord(JdbcTemplate jdbcTemplate, String key, CheckTask task) {
        String primaryKey = getPrimaryKey(task);
        List<String> columns = getSelectColumns(task);
        String columnStr = String.join(", ", columns);

        StringBuilder sql = new StringBuilder("SELECT ").append(columnStr)
                .append(" FROM ").append(task.getTableName())
                .append(" WHERE ").append(primaryKey).append(" = ?");

        if (task.getWhereCondition() != null && !task.getWhereCondition().isEmpty()) {
            sql.append(" AND (").append(task.getWhereCondition()).append(")");
        }

        try {
            List<DataRecord> records = jdbcTemplate.query(sql.toString(),
                    new Object[]{key}, new DataRecordRowMapper(task, primaryKey));
            return records.isEmpty() ? null : records.get(0);
        } catch (DataAccessException e) {
            log.error("Failed to get record, key: {}, table: {}", key, task.getTableName(), e);
            return null;
        }
    }

    private long getCount(JdbcTemplate jdbcTemplate, CheckTask task) {
        StringBuilder sql = new StringBuilder("SELECT COUNT(*) FROM ").append(task.getTableName());
        if (task.getWhereCondition() != null && !task.getWhereCondition().isEmpty()) {
            sql.append(" WHERE ").append(task.getWhereCondition());
        }
        try {
            Long count = jdbcTemplate.queryForObject(sql.toString(), Long.class);
            return count != null ? count : 0;
        } catch (DataAccessException e) {
            log.error("Failed to get count for table: {}", task.getTableName(), e);
            return 0;
        }
    }

    private boolean executeInsert(JdbcTemplate jdbcTemplate, DataRecord record, CheckTask task) {
        List<String> columns = getInsertColumns(record, task);
        String columnStr = String.join(", ", columns);
        String placeholders = columns.stream().map(c -> "?").collect(Collectors.joining(", "));
        Object[] values = columns.stream().map(record.getData()::get).toArray();

        String sql = "INSERT INTO " + task.getTableName() + " (" + columnStr + ") VALUES (" + placeholders + ")";
        try {
            jdbcTemplate.update(sql, values);
            log.info("Successfully inserted record, key: {}, table: {}", record.getKey(), task.getTableName());
            return true;
        } catch (DataAccessException e) {
            log.error("Failed to insert record, key: {}, table: {}", record.getKey(), task.getTableName(), e);
            return false;
        }
    }

    private boolean executeUpdate(JdbcTemplate jdbcTemplate, DataRecord record, CheckTask task) {
        String primaryKey = getPrimaryKey(task);
        List<String> updateColumns = getUpdateColumns(record, task, primaryKey);
        String setClause = updateColumns.stream().map(c -> c + " = ?").collect(Collectors.joining(", "));
        List<Object> values = updateColumns.stream().map(record.getData()::get).collect(Collectors.toList());
        values.add(record.getKey());

        String sql = "UPDATE " + task.getTableName() + " SET " + setClause + " WHERE " + primaryKey + " = ?";
        try {
            int affected = jdbcTemplate.update(sql, values.toArray());
            if (affected > 0) {
                log.info("Successfully updated record, key: {}, table: {}", record.getKey(), task.getTableName());
                return true;
            }
            log.warn("No record updated, key: {}, table: {}", record.getKey(), task.getTableName());
            return false;
        } catch (DataAccessException e) {
            log.error("Failed to update record, key: {}, table: {}", record.getKey(), task.getTableName(), e);
            return false;
        }
    }

    private boolean executeDelete(JdbcTemplate jdbcTemplate, String key, CheckTask task) {
        String primaryKey = getPrimaryKey(task);
        String sql = "DELETE FROM " + task.getTableName() + " WHERE " + primaryKey + " = ?";
        try {
            int affected = jdbcTemplate.update(sql, key);
            if (affected > 0) {
                log.info("Successfully deleted record, key: {}, table: {}", key, task.getTableName());
                return true;
            }
            log.warn("No record deleted, key: {}, table: {}", key, task.getTableName());
            return false;
        } catch (DataAccessException e) {
            log.error("Failed to delete record, key: {}, table: {}", key, task.getTableName(), e);
            return false;
        }
    }

    private String getPrimaryKey(CheckTask task) {
        if (task.getPrimaryKey() != null && !task.getPrimaryKey().isEmpty()) {
            return task.getPrimaryKey();
        }
        List<String> primaryKeys = getPrimaryKeys(task.getTableName());
        return primaryKeys.isEmpty() ? "id" : primaryKeys.get(0);
    }

    private List<String> getSelectColumns(CheckTask task) {
        List<String> columns;
        if (task.getCompareFields() != null && !task.getCompareFields().isEmpty()) {
            columns = new ArrayList<>(task.getCompareFields());
            String primaryKey = getPrimaryKey(task);
            if (!columns.contains(primaryKey)) {
                columns.add(0, primaryKey);
            }
        } else {
            columns = new ArrayList<>(getColumns(task.getTableName()));
        }
        if (task.getExcludeFields() != null && !task.getExcludeFields().isEmpty()) {
            columns.removeAll(task.getExcludeFields());
        }
        return columns;
    }

    private List<String> getInsertColumns(DataRecord record, CheckTask task) {
        List<String> columns = new ArrayList<>(record.getData().keySet());
        if (task.getExcludeFields() != null && !task.getExcludeFields().isEmpty()) {
            columns.removeAll(task.getExcludeFields());
        }
        return columns;
    }

    private List<String> getUpdateColumns(DataRecord record, CheckTask task, String primaryKey) {
        List<String> columns = new ArrayList<>(record.getData().keySet());
        columns.remove(primaryKey);
        if (task.getExcludeFields() != null && !task.getExcludeFields().isEmpty()) {
            columns.removeAll(task.getExcludeFields());
        }
        return columns;
    }

    private class MysqlRecordIterator implements Iterator<DataRecord> {
        private final JdbcTemplate jdbcTemplate;
        private final CheckTask task;
        private final int batchSize;
        private int offset = 0;
        private List<DataRecord> currentBatch;
        private int currentIndex = 0;
        private boolean hasMore = true;
        private final String primaryKey;
        private final List<String> columns;
        private final String baseSql;

        public MysqlRecordIterator(JdbcTemplate jdbcTemplate, CheckTask task) {
            this.jdbcTemplate = jdbcTemplate;
            this.task = task;
            this.batchSize = task.getBatchSize() != null ? task.getBatchSize() : 1000;
            this.primaryKey = getPrimaryKey(task);
            this.columns = getSelectColumns(task);
            this.baseSql = buildBaseSql();
            fetchNextBatch();
        }

        private String buildBaseSql() {
            String columnStr = String.join(", ", columns);
            StringBuilder sql = new StringBuilder("SELECT ").append(columnStr)
                    .append(" FROM ").append(task.getTableName());
            if (task.getWhereCondition() != null && !task.getWhereCondition().isEmpty()) {
                sql.append(" WHERE ").append(task.getWhereCondition());
            }
            sql.append(" ORDER BY ").append(primaryKey);
            sql.append(" LIMIT ? OFFSET ?");
            return sql.toString();
        }

        private void fetchNextBatch() {
            try {
                currentBatch = jdbcTemplate.query(baseSql,
                        new Object[]{batchSize, offset},
                        new DataRecordRowMapper(task, primaryKey));
                if (currentBatch.isEmpty()) {
                    hasMore = false;
                    currentBatch = Collections.emptyList();
                } else {
                    offset += currentBatch.size();
                    currentIndex = 0;
                }
            } catch (DataAccessException e) {
                log.error("Failed to fetch batch, offset: {}, table: {}", offset, task.getTableName(), e);
                hasMore = false;
                currentBatch = Collections.emptyList();
            }
        }

        @Override
        public boolean hasNext() {
            if (currentIndex < currentBatch.size()) {
                return true;
            }
            if (hasMore) {
                fetchNextBatch();
                return currentIndex < currentBatch.size();
            }
            return false;
        }

        @Override
        public DataRecord next() {
            if (!hasNext()) {
                throw new NoSuchElementException();
            }
            return currentBatch.get(currentIndex++);
        }
    }

    private class DataRecordRowMapper implements RowMapper<DataRecord> {
        private final CheckTask task;
        private final String primaryKey;

        public DataRecordRowMapper(CheckTask task, String primaryKey) {
            this.task = task;
            this.primaryKey = primaryKey;
        }

        @Override
        public DataRecord mapRow(ResultSet rs, int rowNum) throws SQLException {
            Map<String, Object> data = new LinkedHashMap<>();
            ResultSetMetaData metaData = rs.getMetaData();
            int columnCount = metaData.getColumnCount();
            String key = null;

            for (int i = 1; i <= columnCount; i++) {
                String columnName = metaData.getColumnLabel(i);
                Object value = rs.getObject(i);
                data.put(columnName, value);
                if (columnName.equalsIgnoreCase(primaryKey)) {
                    key = value != null ? value.toString() : null;
                }
            }

            return DataRecord.builder()
                    .key(key)
                    .data(data)
                    .sourceType(DataSourceType.MYSQL)
                    .timestamp(System.currentTimeMillis())
                    .tableName(task.getTableName())
                    .build();
        }
    }
}

package com.datatransfer.migration.adapter;

import com.datatransfer.migration.engine.CheckpointInfo;
import com.datatransfer.migration.engine.DataSourceReader;
import com.datatransfer.migration.engine.DataSourceWriter;
import com.datatransfer.migration.engine.Record;
import com.datatransfer.migration.model.DataSource;
import lombok.extern.slf4j.Slf4j;

import java.sql.*;
import java.util.*;

@Slf4j
public class MysqlDataSourceAdapter implements DataSourceAdapter {
    private final DataSource dataSource;
    private Connection connection;

    public MysqlDataSourceAdapter(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    private Connection getConnection() throws SQLException {
        if (connection == null || connection.isClosed()) {
            Map<String, Object> config = dataSource.getConfig();
            String host = (String) config.get("host");
            String port = String.valueOf(config.get("port"));
            String database = (String) config.get("database");
            String username = (String) config.get("username");
            String password = (String) config.get("password");
            String url = String.format("jdbc:mysql://%s:%s/%s?useUnicode=true&characterEncoding=utf8&useSSL=false&serverTimezone=Asia/Shanghai",
                    host, port, database);
            connection = DriverManager.getConnection(url, username, password);
        }
        return connection;
    }

    @Override
    public boolean testConnection() {
        try (Connection conn = getConnection()) {
            return conn.isValid(5);
        } catch (SQLException e) {
            log.error("Connection test failed", e);
            return false;
        }
    }

    @Override
    public DataSourceReader createReader() {
        return new MysqlDataSourceReader();
    }

    @Override
    public DataSourceWriter createWriter() {
        return new MysqlDataSourceWriter();
    }

    @Override
    public List<String> listTables() {
        List<String> tables = new ArrayList<>();
        try (Connection conn = getConnection();
             ResultSet rs = conn.getMetaData().getTables(conn.getCatalog(), null, "%", new String[]{"TABLE"})) {
            while (rs.next()) {
                tables.add(rs.getString("TABLE_NAME"));
            }
        } catch (SQLException e) {
            log.error("Error listing tables", e);
        }
        return tables;
    }

    @Override
    public Map<String, String> getTableSchema(String tableName) {
        Map<String, String> schema = new LinkedHashMap<>();
        try (Connection conn = getConnection();
             ResultSet rs = conn.getMetaData().getColumns(conn.getCatalog(), null, tableName, null)) {
            while (rs.next()) {
                schema.put(rs.getString("COLUMN_NAME"), rs.getString("TYPE_NAME"));
            }
        } catch (SQLException e) {
            log.error("Error getting table schema", e);
        }
        return schema;
    }

    private class MysqlDataSourceReader implements DataSourceReader {
        private Connection conn;
        private Statement stmt;
        private ResultSet rs;
        private ResultSetMetaData metaData;
        private long totalCount = 0;
        private String tableName;
        private String primaryKey;
        private long currentRowId = 0;
        private long rowsFetched = 0;

        @Override
        public void open(Map<String, Object> config) throws Exception {
            openFromPosition(config, null);
        }

        @Override
        public void openFromPosition(Map<String, Object> config, CheckpointInfo checkpoint) throws Exception {
            conn = getConnection();
            tableName = (String) config.get("tableName");
            primaryKey = (String) config.get("primaryKey");
            if (primaryKey == null || primaryKey.isEmpty()) {
                primaryKey = "id";
            }

            if (checkpoint != null && "row_offset".equals(checkpoint.getPositionType())) {
                currentRowId = Long.parseLong(checkpoint.getPositionValue());
                log.info("Resuming from row offset: {}", currentRowId);
            }

            stmt = conn.createStatement(ResultSet.TYPE_FORWARD_ONLY, ResultSet.CONCUR_READ_ONLY);
            stmt.setFetchSize(Integer.MIN_VALUE);

            try (Statement countStmt = conn.createStatement();
                 ResultSet countRs = countStmt.executeQuery("SELECT COUNT(*) FROM " + tableName)) {
                if (countRs.next()) {
                    totalCount = countRs.getLong(1);
                }
            }

            String sql;
            if (currentRowId > 0) {
                sql = String.format("SELECT * FROM %s WHERE %s > %d ORDER BY %s ASC", tableName, primaryKey, currentRowId, primaryKey);
            } else {
                sql = "SELECT * FROM " + tableName + " ORDER BY " + primaryKey + " ASC";
            }
            rs = stmt.executeQuery(sql);
            metaData = rs.getMetaData();
        }

        @Override
        public boolean hasNext() {
            try {
                return rs.next();
            } catch (SQLException e) {
                log.error("Error checking next record", e);
                return false;
            }
        }

        @Override
        public Record next() {
            try {
                Record record = new Record();
                record.setTableName(tableName);
                int columnCount = metaData.getColumnCount();
                for (int i = 1; i <= columnCount; i++) {
                    String columnName = metaData.getColumnName(i);
                    Object value = rs.getObject(i);
                    record.set(columnName, value);
                    if (columnName.equals(primaryKey) && value instanceof Number) {
                        currentRowId = ((Number) value).longValue();
                    }
                }
                rowsFetched++;
                return record;
            } catch (SQLException e) {
                throw new RuntimeException("Error reading record", e);
            }
        }

        @Override
        public List<Record> nextBatch(int batchSize) {
            List<Record> batch = new ArrayList<>(batchSize);
            int count = 0;
            while (count < batchSize && hasNext()) {
                batch.add(next());
                count++;
            }
            return batch;
        }

        @Override
        public long getTotalCount() {
            return totalCount;
        }

        @Override
        public CheckpointInfo currentCheckpoint() {
            CheckpointInfo cp = new CheckpointInfo();
            cp.setPositionType("row_offset");
            cp.setPositionValue(String.valueOf(currentRowId));
            cp.setProcessedRecords(rowsFetched);
            return cp;
        }

        @Override
        public void close() throws Exception {
            if (rs != null) rs.close();
            if (stmt != null) stmt.close();
        }
    }

    private class MysqlDataSourceWriter implements DataSourceWriter {
        private Connection conn;
        private String tableName;
        private List<String> columns;
        private List<Record> pendingBatch = new ArrayList<>();
        private static final int BATCH_SIZE = 500;

        @Override
        public void open(Map<String, Object> config) throws Exception {
            conn = getConnection();
            conn.setAutoCommit(false);
            tableName = (String) config.get("targetTableName");
            if (tableName == null) {
                tableName = (String) config.get("tableName");
            }
        }

        @Override
        public void write(Record record) throws Exception {
            pendingBatch.add(record);
            if (pendingBatch.size() >= BATCH_SIZE) {
                executeBatch();
            }
        }

        @Override
        public void writeBatch(List<Record> records) throws Exception {
            pendingBatch.addAll(records);
            if (pendingBatch.size() >= BATCH_SIZE) {
                executeBatch();
            }
        }

        @Override
        public void flush() {
            if (!pendingBatch.isEmpty()) {
                executeBatch();
            }
        }

        private void executeBatch() {
            if (pendingBatch.isEmpty()) return;
            try {
                if (columns == null) {
                    columns = new ArrayList<>(pendingBatch.get(0).getData().keySet());
                }
                String sql = buildInsertSql();
                try (PreparedStatement pstmt = conn.prepareStatement(sql)) {
                    for (Record record : pendingBatch) {
                        int idx = 1;
                        for (String column : columns) {
                            pstmt.setObject(idx++, record.get(column));
                        }
                        pstmt.addBatch();
                    }
                    pstmt.executeBatch();
                    conn.commit();
                }
                pendingBatch.clear();
            } catch (SQLException e) {
                log.error("Error executing batch insert", e);
                try { conn.rollback(); } catch (SQLException ex) { log.error("Error rolling back", ex); }
                throw new RuntimeException(e);
            }
        }

        private String buildInsertSql() {
            StringBuilder sql = new StringBuilder("INSERT INTO ");
            sql.append(tableName).append(" (");
            sql.append(String.join(", ", columns));
            sql.append(") VALUES (");
            sql.append(String.join(", ", Collections.nCopies(columns.size(), "?")));
            sql.append(")");
            return sql.toString();
        }

        @Override
        public void close() throws Exception {
            flush();
            if (conn != null) {
                conn.setAutoCommit(true);
            }
        }
    }
}

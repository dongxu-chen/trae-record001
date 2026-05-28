package com.datasync.validator;

import com.datasync.common.enums.DatabaseType;
import lombok.Builder;
import lombok.extern.slf4j.Slf4j;

import javax.sql.DataSource;
import java.sql.*;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Slf4j
public class DataValidatorService {
    private final DataSource sourceDataSource;
    private final DataSource targetDataSource;
    private final DatabaseType sourceDbType;
    private final DatabaseType targetDbType;
    private final String sourceDatacenterId;
    private final String targetDatacenterId;
    private final int defaultSampleSize;
    private final long validationIntervalMinutes;
    private final double alertThreshold;
    private final Map<String, DataValidationResult> lastResults = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler;
    private final Set<String> tablesToValidate;
    private volatile boolean running = false;

    @Builder
    public DataValidatorService(DataSource sourceDataSource,
                                DataSource targetDataSource,
                                DatabaseType sourceDbType,
                                DatabaseType targetDbType,
                                String sourceDatacenterId,
                                String targetDatacenterId,
                                Integer defaultSampleSize,
                                Long validationIntervalMinutes,
                                Double alertThreshold,
                                Set<String> tablesToValidate) {
        this.sourceDataSource = sourceDataSource;
        this.targetDataSource = targetDataSource;
        this.sourceDbType = sourceDbType;
        this.targetDbType = targetDbType;
        this.sourceDatacenterId = sourceDatacenterId;
        this.targetDatacenterId = targetDatacenterId;
        this.defaultSampleSize = defaultSampleSize != null ? defaultSampleSize : 1000;
        this.validationIntervalMinutes = validationIntervalMinutes != null ? validationIntervalMinutes : 60;
        this.alertThreshold = alertThreshold != null ? alertThreshold : 99.0;
        this.tablesToValidate = tablesToValidate;
        this.scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "data-validator");
            t.setDaemon(true);
            return t;
        });
    }

    public void start() {
        if (running) return;
        running = true;
        log.info("Starting Data Validator Service between {} and {}", sourceDatacenterId, targetDatacenterId);

        scheduler.scheduleAtFixedRate(
                this::validateAllTables,
                validationIntervalMinutes,
                validationIntervalMinutes,
                TimeUnit.MINUTES
        );

        log.info("Data Validator Service started, interval: {} minutes", validationIntervalMinutes);
    }

    public void stop() {
        if (!running) return;
        running = false;
        scheduler.shutdown();
        log.info("Data Validator Service stopped");
    }

    public void validateAllTables() {
        if (!running) return;
        log.info("Starting validation for all tables between {} and {}", sourceDatacenterId, targetDatacenterId);

        for (String tableName : tablesToValidate) {
            try {
                DataValidationResult result = validateTable(tableName, defaultSampleSize);
                lastResults.put(tableName, result);

                if (result.getMatchRate() < alertThreshold) {
                    log.warn("Validation alert for table {}: match rate {}% below threshold {}%",
                            tableName, String.format("%.2f", result.getMatchRate()), alertThreshold);
                }

                log.info("Validation completed for {}: match rate {}%, mismatches {}, missing {}",
                        tableName, String.format("%.2f", result.getMatchRate()),
                        result.getMismatchCount(), result.getMissingCount());
            } catch (Exception e) {
                log.error("Validation failed for table: {}", tableName, e);
            }
        }
    }

    public DataValidationResult validateTable(String tableName, int sampleSize) throws SQLException {
        LocalDateTime startTime = LocalDateTime.now();
        long startMs = System.currentTimeMillis();

        log.info("Validating table: {}, sample size: {}", tableName, sampleSize);

        DataValidationResult result = DataValidationResult.builder()
                .validationId(UUID.randomUUID().toString())
                .sourceDatacenterId(sourceDatacenterId)
                .targetDatacenterId(targetDatacenterId)
                .tableName(tableName)
                .startTime(startTime)
                .build();

        List<String> primaryKeys = getPrimaryKeys(sourceDataSource, tableName);
        if (primaryKeys.isEmpty()) {
            throw new SQLException("No primary keys found for table: " + tableName);
        }

        List<Map<String, Object>> sourceSamples = sampleTable(sourceDataSource, tableName, primaryKeys, sampleSize, sourceDbType);
        if (sourceSamples.isEmpty()) {
            result.setSuccess(true);
            result.setSampleSize(0);
            result.setMatchCount(0);
            result.setMatchRate(100.0);
            result.setEndTime(LocalDateTime.now());
            result.setDurationMs(System.currentTimeMillis() - startMs);
            return result;
        }

        result.setSampleSize(sourceSamples.size());

        Map<String, Map<String, Object>> targetRows = fetchRows(targetDataSource, tableName, primaryKeys, sourceSamples, targetDbType);

        long matchCount = 0;
        long mismatchCount = 0;
        long missingCount = 0;
        List<DataValidationResult.MismatchDetail> mismatchDetails = new ArrayList<>();

        for (Map<String, Object> sourceRow : sourceSamples) {
            String pkValue = getPrimaryKeyValue(sourceRow, primaryKeys);
            Map<String, Object> targetRow = targetRows.get(pkValue);

            if (targetRow == null) {
                missingCount++;
                DataValidationResult.MismatchDetail detail = DataValidationResult.MismatchDetail.builder()
                        .primaryKey(pkValue)
                        .mismatchType("MISSING_IN_TARGET")
                        .build();
                mismatchDetails.add(detail);
                continue;
            }

            boolean rowMatched = true;
            for (Map.Entry<String, Object> entry : sourceRow.entrySet()) {
                String colName = entry.getKey();
                if (primaryKeys.contains(colName)) continue;

                Object sourceValue = entry.getValue();
                Object targetValue = targetRow.get(colName);

                if (!valuesEqual(sourceValue, targetValue)) {
                    rowMatched = false;
                    DataValidationResult.MismatchDetail detail = DataValidationResult.MismatchDetail.builder()
                            .primaryKey(pkValue)
                            .columnName(colName)
                            .sourceValue(sourceValue)
                            .targetValue(targetValue)
                            .mismatchType("VALUE_MISMATCH")
                            .build();
                    mismatchDetails.add(detail);
                }
            }

            if (rowMatched) {
                matchCount++;
            } else {
                mismatchCount++;
            }

            if (mismatchDetails.size() >= 100) {
                break;
            }
        }

        double matchRate = result.getSampleSize() > 0
                ? (double) matchCount / result.getSampleSize() * 100.0
                : 100.0;

        result.setMatchCount(matchCount);
        result.setMismatchCount(mismatchCount);
        result.setMissingCount(missingCount);
        result.setMatchRate(matchRate);
        result.setSuccess(true);
        result.setEndTime(LocalDateTime.now());
        result.setDurationMs(System.currentTimeMillis() - startMs);
        result.setMismatchDetails(mismatchDetails);

        log.debug("Validation result for {}: match rate {}%, matches: {}, mismatches: {}, missing: {}",
                tableName, String.format("%.2f", matchRate), matchCount, mismatchCount, missingCount);

        return result;
    }

    private List<String> getPrimaryKeys(DataSource dataSource, String tableName) throws SQLException {
        List<String> primaryKeys = new ArrayList<>();
        try (Connection conn = dataSource.getConnection()) {
            DatabaseMetaData metaData = conn.getMetaData();
            String[] parts = tableName.split("\\.");
            String schema = parts.length > 1 ? parts[0] : null;
            String table = parts.length > 1 ? parts[1] : tableName;

            try (ResultSet rs = metaData.getPrimaryKeys(null, schema, table)) {
                while (rs.next()) {
                    primaryKeys.add(rs.getString("COLUMN_NAME"));
                }
            }
        }
        return primaryKeys;
    }

    private List<Map<String, Object>> sampleTable(DataSource dataSource, String tableName,
                                                   List<String> primaryKeys, int sampleSize,
                                                   DatabaseType dbType) throws SQLException {
        List<Map<String, Object>> rows = new ArrayList<>();
        String sql;

        if (dbType == DatabaseType.MYSQL) {
            sql = String.format("SELECT * FROM %s ORDER BY RAND() LIMIT ?", tableName);
        } else if (dbType == DatabaseType.POSTGRESQL) {
            sql = String.format("SELECT * FROM %s ORDER BY RANDOM() LIMIT ?", tableName);
        } else {
            sql = String.format("SELECT * FROM %s LIMIT ?", tableName);
        }

        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, sampleSize);
            try (ResultSet rs = ps.executeQuery()) {
                ResultSetMetaData metaData = rs.getMetaData();
                int columnCount = metaData.getColumnCount();

                while (rs.next()) {
                    Map<String, Object> row = new HashMap<>();
                    for (int i = 1; i <= columnCount; i++) {
                        String colName = metaData.getColumnName(i);
                        row.put(colName, rs.getObject(i));
                    }
                    rows.add(row);
                }
            }
        }
        return rows;
    }

    private Map<String, Map<String, Object>> fetchRows(DataSource dataSource, String tableName,
                                                        List<String> primaryKeys,
                                                        List<Map<String, Object>> sourceSamples,
                                                        DatabaseType dbType) throws SQLException {
        Map<String, Map<String, Object>> result = new HashMap<>();
        if (sourceSamples.isEmpty()) return result;

        StringBuilder inClause = new StringBuilder();
        for (int i = 0; i < primaryKeys.size(); i++) {
            if (i > 0) inClause.append(", ");
            inClause.append(primaryKeys.get(i));
        }

        StringBuilder placeholders = new StringBuilder();
        for (int i = 0; i < sourceSamples.size(); i++) {
            if (i > 0) placeholders.append(", ");
            if (primaryKeys.size() == 1) {
                placeholders.append("?");
            } else {
                placeholders.append("(");
                for (int j = 0; j < primaryKeys.size(); j++) {
                    if (j > 0) placeholders.append(", ");
                    placeholders.append("?");
                }
                placeholders.append(")");
            }
        }

        String sql = String.format("SELECT * FROM %s WHERE (%s) IN (%s)",
                tableName, inClause, placeholders);

        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            int paramIndex = 1;
            for (Map<String, Object> row : sourceSamples) {
                for (String pk : primaryKeys) {
                    ps.setObject(paramIndex++, row.get(pk));
                }
            }

            try (ResultSet rs = ps.executeQuery()) {
                ResultSetMetaData metaData = rs.getMetaData();
                int columnCount = metaData.getColumnCount();

                while (rs.next()) {
                    Map<String, Object> row = new HashMap<>();
                    for (int i = 1; i <= columnCount; i++) {
                        String colName = metaData.getColumnName(i);
                        row.put(colName, rs.getObject(i));
                    }
                    String pkValue = getPrimaryKeyValue(row, primaryKeys);
                    result.put(pkValue, row);
                }
            }
        }
        return result;
    }

    private String getPrimaryKeyValue(Map<String, Object> row, List<String> primaryKeys) {
        if (primaryKeys.size() == 1) {
            return String.valueOf(row.get(primaryKeys.get(0)));
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < primaryKeys.size(); i++) {
            if (i > 0) sb.append("|");
            sb.append(row.get(primaryKeys.get(i)));
        }
        return sb.toString();
    }

    private boolean valuesEqual(Object o1, Object o2) {
        if (o1 == null && o2 == null) return true;
        if (o1 == null || o2 == null) return false;

        if (o1 instanceof Number && o2 instanceof Number) {
            return ((Number) o1).doubleValue() == ((Number) o2).doubleValue();
        }

        if (o1 instanceof byte[] && o2 instanceof byte[]) {
            return Arrays.equals((byte[]) o1, (byte[]) o2);
        }

        return o1.equals(o2);
    }

    public Map<String, DataValidationResult> getLastResults() {
        return new HashMap<>(lastResults);
    }

    public DataValidationResult getLastResult(String tableName) {
        return lastResults.get(tableName);
    }

    public boolean isRunning() {
        return running;
    }
}

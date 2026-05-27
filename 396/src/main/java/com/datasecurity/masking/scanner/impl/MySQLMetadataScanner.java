package com.datasecurity.masking.scanner.impl;

import com.datasecurity.masking.enums.DatabaseType;
import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.model.DatabaseConfig;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.recognizer.SensitiveFieldRecognizer;
import com.datasecurity.masking.scanner.MetadataScanner;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
public class MySQLMetadataScanner implements MetadataScanner {

    @Autowired
    private SensitiveFieldRecognizer recognizer;

    @Override
    public boolean support(DatabaseConfig config) {
        return DatabaseType.MYSQL.equals(config.getType());
    }

    @Override
    public List<SensitiveField> scan(DatabaseConfig config) {
        List<SensitiveField> sensitiveFields = new ArrayList<>();
        String url = buildConnectionUrl(config);

        try (Connection conn = DriverManager.getConnection(url, config.getUsername(), config.getPassword());
             Statement stmt = conn.createStatement()) {

            String databaseName = config.getDatabase();
            String sql = "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, COLUMN_COMMENT " +
                    "FROM INFORMATION_SCHEMA.COLUMNS " +
                    "WHERE TABLE_SCHEMA = '" + databaseName + "' " +
                    "AND DATA_TYPE IN ('varchar', 'char', 'text', 'mediumtext', 'longtext')";

            try (ResultSet rs = stmt.executeQuery(sql)) {
                while (rs.next()) {
                    String tableName = rs.getString("TABLE_NAME");
                    String columnName = rs.getString("COLUMN_NAME");
                    String comment = rs.getString("COLUMN_COMMENT");
                    int dataLength = rs.getInt("CHARACTER_MAXIMUM_LENGTH");

                    SensitiveType sensitiveType = recognizer.recognizeByColumnName(columnName, comment);

                    if (!SensitiveType.UNKNOWN.equals(sensitiveType)) {
                        sensitiveFields.add(SensitiveField.builder()
                                .tableName(tableName)
                                .columnName(columnName)
                                .sensitiveType(sensitiveType)
                                .comment(comment)
                                .dataLength(dataLength)
                                .build());
                        log.info("Found sensitive field in MySQL: {}.{} -> {}", tableName, columnName, sensitiveType);
                    }
                }
            }
        } catch (SQLException e) {
            log.error("Failed to scan MySQL metadata for database: {}", config.getName(), e);
            throw new RuntimeException("Failed to scan MySQL metadata", e);
        }

        return sensitiveFields;
    }

    private String buildConnectionUrl(DatabaseConfig config) {
        if (config.getConnectionUrl() != null && !config.getConnectionUrl().isEmpty()) {
            return config.getConnectionUrl();
        }
        return String.format("jdbc:mysql://%s:%d/%s?useUnicode=true&characterEncoding=utf8&useSSL=false",
                config.getHost(), config.getPort(), config.getDatabase());
    }
}

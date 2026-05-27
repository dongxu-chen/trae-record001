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
public class PostgreSQLMetadataScanner implements MetadataScanner {

    @Autowired
    private SensitiveFieldRecognizer recognizer;

    @Override
    public boolean support(DatabaseConfig config) {
        return DatabaseType.POSTGRESQL.equals(config.getType());
    }

    @Override
    public List<SensitiveField> scan(DatabaseConfig config) {
        List<SensitiveField> sensitiveFields = new ArrayList<>();
        String url = buildConnectionUrl(config);

        try (Connection conn = DriverManager.getConnection(url, config.getUsername(), config.getPassword());
             Statement stmt = conn.createStatement()) {

            String schemaName = "public";
            String sql = "SELECT table_name, column_name, data_type, character_maximum_length, " +
                    "pg_catalog.col_description(format('%s.%s', table_schema, table_name)::regclass::oid, ordinal_position) as column_comment " +
                    "FROM information_schema.columns " +
                    "WHERE table_schema = '" + schemaName + "' " +
                    "AND data_type IN ('character varying', 'character', 'text', 'varchar', 'char')";

            try (ResultSet rs = stmt.executeQuery(sql)) {
                while (rs.next()) {
                    String tableName = rs.getString("table_name");
                    String columnName = rs.getString("column_name");
                    String comment = rs.getString("column_comment");
                    int dataLength = rs.getInt("character_maximum_length");

                    SensitiveType sensitiveType = recognizer.recognizeByColumnName(columnName, comment);

                    if (!SensitiveType.UNKNOWN.equals(sensitiveType)) {
                        sensitiveFields.add(SensitiveField.builder()
                                .tableName(tableName)
                                .columnName(columnName)
                                .sensitiveType(sensitiveType)
                                .comment(comment)
                                .dataLength(dataLength)
                                .build());
                        log.info("Found sensitive field in PostgreSQL: {}.{} -> {}", tableName, columnName, sensitiveType);
                    }
                }
            }
        } catch (SQLException e) {
            log.error("Failed to scan PostgreSQL metadata for database: {}", config.getName(), e);
            throw new RuntimeException("Failed to scan PostgreSQL metadata", e);
        }

        return sensitiveFields;
    }

    private String buildConnectionUrl(DatabaseConfig config) {
        if (config.getConnectionUrl() != null && !config.getConnectionUrl().isEmpty()) {
            return config.getConnectionUrl();
        }
        return String.format("jdbc:postgresql://%s:%d/%s",
                config.getHost(), config.getPort(), config.getDatabase());
    }
}

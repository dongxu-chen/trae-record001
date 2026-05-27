package com.datasecurity.masking.audit;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditLog {

    private String id;

    private Long timestamp;

    private String userId;

    private String username;

    private String userRole;

    private String operation;

    private String databaseId;

    private String tableName;

    private List<String> sensitiveColumns;

    private List<String> sensitiveTypes;

    private String sql;

    private Integer rowCount;

    private String clientIp;

    private String userAgent;

    private String requestId;

    private Map<String, Object> additionalInfo;

    private boolean masked;

    private Long executionTime;

    public enum OperationType {
        QUERY, EXPORT, INSERT, UPDATE, DELETE, MASKING, ADMIN
    }
}

package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DatabaseConstraint {
    private int maxDatabaseConnections;
    private int sharedByApplications;
    private int reservedConnections;
    private String databaseType;

    public static DatabaseConstraint defaultConstraint() {
        return DatabaseConstraint.builder()
                .maxDatabaseConnections(200)
                .sharedByApplications(1)
                .reservedConnections(10)
                .databaseType("MySQL")
                .build();
    }

    public int getAvailableConnections() {
        if (sharedByApplications <= 0) sharedByApplications = 1;
        return Math.max(1, (maxDatabaseConnections - reservedConnections) / sharedByApplications);
    }
}

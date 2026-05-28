package com.datasync.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DDLEvent implements Serializable {

    private static final long serialVersionUID = 1L;

    private String database;

    private String table;

    private DDLType ddlType;

    private String sql;

    private List<ColumnChange> columnChanges = new ArrayList<>();

    private long timestamp;

    private String binlogFileName;

    private long binlogPosition;

    public enum DDLType {
        CREATE_TABLE,
        ALTER_TABLE,
        DROP_TABLE,
        TRUNCATE_TABLE,
        RENAME_TABLE,
        CREATE_INDEX,
        DROP_INDEX,
        UNKNOWN
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ColumnChange implements Serializable {
        private static final long serialVersionUID = 1L;

        private ChangeType changeType;

        private String columnName;

        private String oldColumnName;

        private String dataType;

        private Integer length;

        private Integer precision;

        private Integer scale;

        private Boolean nullable;

        private String defaultValue;

        private String comment;

        private Integer position;

        private String afterColumn;

        public enum ChangeType {
            ADD,
            MODIFY,
            DROP,
            CHANGE,
            RENAME
        }
    }

    public boolean isTableRelevant(String schema, String tableName) {
        return (this.database != null && this.database.equals(schema)
                && this.table != null && this.table.equals(tableName);
    }
}

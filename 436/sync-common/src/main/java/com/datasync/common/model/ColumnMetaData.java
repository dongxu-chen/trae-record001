package com.datasync.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ColumnMetaData implements Serializable {
    private static final long serialVersionUID = 1L;

    private String columnName;

    private int columnType;

    private String columnTypeName;

    private String columnClassName;

    private int precision;

    private int scale;

    private boolean isNullable;

    private boolean isPrimaryKey;

    private boolean isAutoIncrement;

    private String defaultValue;

    private int ordinalPosition;
}

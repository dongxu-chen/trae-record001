package com.datasync.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RowData implements Serializable {
    private static final long serialVersionUID = 1L;

    @Builder.Default
    private Map<String, Object> beforeColumns = new HashMap<>();

    @Builder.Default
    private Map<String, Object> afterColumns = new HashMap<>();

    public Object getBeforeValue(String columnName) {
        return beforeColumns.get(columnName);
    }

    public Object getAfterValue(String columnName) {
        return afterColumns.get(columnName);
    }

    public void addBeforeColumn(String columnName, Object value) {
        beforeColumns.put(columnName, value);
    }

    public void addAfterColumn(String columnName, Object value) {
        afterColumns.put(columnName, value);
    }
}

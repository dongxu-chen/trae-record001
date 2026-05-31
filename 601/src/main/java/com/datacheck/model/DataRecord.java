package com.datacheck.model;

import com.datacheck.model.enums.DataSourceType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DataRecord {
    private String key;
    private Map<String, Object> data;
    private DataSourceType sourceType;
    private long timestamp;
    private String tableName;
    private String operation;
}

package com.datasecurity.masking.dp;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DPQueryRequest {

    private String databaseId;

    private String tableName;

    private String columnName;

    private String operation;

    private Double epsilon;

    private Double delta;

    private Double minValue;

    private Double maxValue;

    private String whereClause;

    private String groupBy;
}

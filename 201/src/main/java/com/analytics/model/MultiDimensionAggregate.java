package com.analytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;
import java.sql.Timestamp;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MultiDimensionAggregate implements Serializable {
    private String dimensionType;
    private String dimensionValue;
    private String eventType;
    private long eventCount;
    private long uniqueUserCount;
    private BigDecimal totalAmount;
    private BigDecimal avgAmount;
    private Timestamp windowStart;
    private Timestamp windowEnd;
    private Timestamp processTime;
}

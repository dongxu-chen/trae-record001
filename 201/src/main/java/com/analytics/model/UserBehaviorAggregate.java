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
public class UserBehaviorAggregate implements Serializable {
    private String userId;
    private String eventType;
    private long eventCount;
    private BigDecimal totalAmount;
    private Timestamp windowStart;
    private Timestamp windowEnd;
    private Timestamp processTime;
}

package com.quota.management.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuotaMarketOrder implements Serializable {

    private static final long serialVersionUID = 1L;

    public enum OrderType {
        SELL,
        BUY
    }

    public enum OrderStatus {
        PENDING,
        PARTIAL,
        FILLED,
        CANCELLED,
        EXPIRED
    }

    private String orderId;

    private OrderType orderType;

    private String tenantId;

    private String tenantName;

    private String granularity;

    private long totalAmount;

    private long filledAmount;

    private long remainingAmount;

    private double pricePerUnit;

    private double totalPrice;

    private double filledPrice;

    private OrderStatus status;

    private LocalDateTime createdAt;

    private LocalDateTime expiresAt;

    private LocalDateTime filledAt;
}

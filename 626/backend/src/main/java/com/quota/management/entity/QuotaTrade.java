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
public class QuotaTrade implements Serializable {

    private static final long serialVersionUID = 1L;

    private String tradeId;

    private String sellOrderId;

    private String buyOrderId;

    private String sellerTenantId;

    private String buyerTenantId;

    private String granularity;

    private long amount;

    private double pricePerUnit;

    private double totalPrice;

    private LocalDateTime tradedAt;
}

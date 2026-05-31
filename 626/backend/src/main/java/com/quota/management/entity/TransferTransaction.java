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
public class TransferTransaction implements Serializable {

    private static final long serialVersionUID = 1L;

    public enum TransactionStatus {
        TRYING,
        CONFIRMED,
        CANCELLED,
        TIMED_OUT
    }

    private String transactionId;

    private String fromTenantId;

    private String toTenantId;

    private String granularity;

    private long amount;

    private TransactionStatus status;

    private long fromVersionBefore;

    private long toVersionBefore;

    private LocalDateTime createdAt;

    private LocalDateTime confirmedAt;

    private LocalDateTime cancelledAt;

    private long timeoutSeconds;
}

package com.dtmonitor.core.enums;

public enum TransactionStatus {
    BEGIN,
    COMMITTING,
    COMMITTED,
    ROLLBACKING,
    ROLLEDBACK,
    TIMEOUT,
    FAILED,
    UNKNOWN
}

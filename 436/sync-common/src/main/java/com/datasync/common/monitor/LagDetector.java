package com.datasync.common.monitor;

public interface LagDetector {
    long getTotalLag();

    boolean isLagSafeForSwitch();

    boolean isLagHigh();

    LagStatus getLagStatus();

    void waitForLagBelowThreshold(long timeoutMs) throws InterruptedException;

    interface LagStatus {
        long getTotalLag();
        long getMaxLag();
        long getHighWatermarkThreshold();
        long getLowWatermarkThreshold();
        boolean isSafeForSwitch();
        boolean isHighLag();
    }
}

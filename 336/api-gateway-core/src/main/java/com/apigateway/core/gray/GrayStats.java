package com.apigateway.core.gray;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

/**
 * 灰度统计实体类
 * 记录v1和v2版本的请求统计信息，使用原子操作保证线程安全
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GrayStats implements Serializable {

    /**
     * v1版本请求数（使用LongAdder保证高并发下的性能）
     */
    @Builder.Default
    private transient LongAdder v1RequestCount = new LongAdder();

    /**
     * v2版本请求数
     */
    @Builder.Default
    private transient LongAdder v2RequestCount = new LongAdder();

    /**
     * v1版本成功请求数
     */
    @Builder.Default
    private transient LongAdder v1SuccessCount = new LongAdder();

    /**
     * v2版本成功请求数
     */
    @Builder.Default
    private transient LongAdder v2SuccessCount = new LongAdder();

    /**
     * v1版本失败请求数
     */
    @Builder.Default
    private transient LongAdder v1FailureCount = new LongAdder();

    /**
     * v2版本失败请求数
     */
    @Builder.Default
    private transient LongAdder v2FailureCount = new LongAdder();

    /**
     * v1版本总延迟（毫秒）
     */
    @Builder.Default
    private transient LongAdder v1TotalLatency = new LongAdder();

    /**
     * v2版本总延迟（毫秒）
     */
    @Builder.Default
    private transient LongAdder v2TotalLatency = new LongAdder();

    /**
     * v1版本最大延迟（毫秒）
     */
    @Builder.Default
    private transient AtomicLong v1MaxLatency = new AtomicLong(0);

    /**
     * v2版本最大延迟（毫秒）
     */
    @Builder.Default
    private transient AtomicLong v2MaxLatency = new AtomicLong(0);

    /**
     * 统计开始时间
     */
    @Builder.Default
    private LocalDateTime startTime = LocalDateTime.now();

    /**
     * 获取v1请求数
     *
     * @return v1请求数
     */
    public long getV1Requests() {
        return v1RequestCount.sum();
    }

    /**
     * 获取v2请求数
     *
     * @return v2请求数
     */
    public long getV2Requests() {
        return v2RequestCount.sum();
    }

    /**
     * 获取v1成功率
     *
     * @return 成功率（0-100）
     */
    public double getV1SuccessRate() {
        long total = getV1Requests();
        if (total == 0) {
            return 100.0;
        }
        return (v1SuccessCount.sum() * 100.0) / total;
    }

    /**
     * 获取v2成功率
     *
     * @return 成功率（0-100）
     */
    public double getV2SuccessRate() {
        long total = getV2Requests();
        if (total == 0) {
            return 100.0;
        }
        return (v2SuccessCount.sum() * 100.0) / total;
    }

    /**
     * 获取v1平均延迟
     *
     * @return 平均延迟（毫秒）
     */
    public double getV1AvgLatency() {
        long total = getV1Requests();
        if (total == 0) {
            return 0.0;
        }
        return v1TotalLatency.sum() / (double) total;
    }

    /**
     * 获取v2平均延迟
     *
     * @return 平均延迟（毫秒）
     */
    public double getV2AvgLatency() {
        long total = getV2Requests();
        if (total == 0) {
            return 0.0;
        }
        return v2TotalLatency.sum() / (double) total;
    }

    /**
     * 记录v1请求
     *
     * @param latency  延迟（毫秒）
     * @param success  是否成功
     */
    public void recordV1Request(long latency, boolean success) {
        v1RequestCount.increment();
        v1TotalLatency.add(latency);
        if (success) {
            v1SuccessCount.increment();
        } else {
            v1FailureCount.increment();
        }
        updateMaxLatency(v1MaxLatency, latency);
    }

    /**
     * 记录v2请求
     *
     * @param latency  延迟（毫秒）
     * @param success  是否成功
     */
    public void recordV2Request(long latency, boolean success) {
        v2RequestCount.increment();
        v2TotalLatency.add(latency);
        if (success) {
            v2SuccessCount.increment();
        } else {
            v2FailureCount.increment();
        }
        updateMaxLatency(v2MaxLatency, latency);
    }

    /**
     * 更新最大延迟
     *
     * @param maxLatency 最大延迟原子变量
     * @param latency    当前延迟
     */
    private void updateMaxLatency(AtomicLong maxLatency, long latency) {
        long currentMax;
        do {
            currentMax = maxLatency.get();
            if (latency <= currentMax) {
                break;
            }
        } while (!maxLatency.compareAndSet(currentMax, latency));
    }

    /**
     * 重置统计数据
     */
    public void reset() {
        v1RequestCount.reset();
        v2RequestCount.reset();
        v1SuccessCount.reset();
        v2SuccessCount.reset();
        v1FailureCount.reset();
        v2FailureCount.reset();
        v1TotalLatency.reset();
        v2TotalLatency.reset();
        v1MaxLatency.set(0);
        v2MaxLatency.set(0);
        startTime = LocalDateTime.now();
    }

    /**
     * 获取统计快照（用于序列化返回）
     *
     * @return 统计快照
     */
    public StatsSnapshot getSnapshot() {
        return StatsSnapshot.builder()
                .v1Requests(getV1Requests())
                .v2Requests(getV2Requests())
                .v1SuccessRate(getV1SuccessRate())
                .v2SuccessRate(getV2SuccessRate())
                .v1AvgLatency(getV1AvgLatency())
                .v2AvgLatency(getV2AvgLatency())
                .v1MaxLatency(v1MaxLatency.get())
                .v2MaxLatency(v2MaxLatency.get())
                .v1Failures(v1FailureCount.sum())
                .v2Failures(v2FailureCount.sum())
                .startTime(startTime)
                .build();
    }

    /**
     * 统计快照类
     * 用于序列化返回给调用方
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StatsSnapshot implements Serializable {

        /**
         * v1请求数
         */
        private long v1Requests;

        /**
         * v2请求数
         */
        private long v2Requests;

        /**
         * v1成功率
         */
        private double v1SuccessRate;

        /**
         * v2成功率
         */
        private double v2SuccessRate;

        /**
         * v1平均延迟（毫秒）
         */
        private double v1AvgLatency;

        /**
         * v2平均延迟（毫秒）
         */
        private double v2AvgLatency;

        /**
         * v1最大延迟（毫秒）
         */
        private long v1MaxLatency;

        /**
         * v2最大延迟（毫秒）
         */
        private long v2MaxLatency;

        /**
         * v1失败数
         */
        private long v1Failures;

        /**
         * v2失败数
         */
        private long v2Failures;

        /**
         * 统计开始时间
         */
        private LocalDateTime startTime;
    }
}

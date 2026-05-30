package com.loganalytics.aggregate;

import com.tdunning.math.stats.MergingDigest;
import com.tdunning.math.stats.TDigest;
import lombok.Data;

import java.io.Serializable;

@Data
public class MetricsAccumulator implements Serializable {
    private long totalRequests = 0;
    private long errorRequests = 0;
    private double totalLatency = 0.0;
    private double minLatency = Double.MAX_VALUE;
    private double maxLatency = Double.MIN_VALUE;
    private double sumOfSquares = 0.0;
    private TDigest tDigest;

    public MetricsAccumulator() {
        this.tDigest = MergingDigest.createDigest(100.0);
    }

    public MetricsAccumulator(double compression) {
        this.tDigest = MergingDigest.createDigest(compression);
    }

    public void add(double latency, boolean isError) {
        totalRequests++;
        if (isError) {
            errorRequests++;
        }

        totalLatency += latency;
        sumOfSquares += latency * latency;

        if (latency < minLatency) {
            minLatency = latency;
        }
        if (latency > maxLatency) {
            maxLatency = latency;
        }

        tDigest.add(latency);
    }

    public void merge(MetricsAccumulator other) {
        this.totalRequests += other.totalRequests;
        this.errorRequests += other.errorRequests;
        this.totalLatency += other.totalLatency;
        this.sumOfSquares += other.sumOfSquares;
        this.minLatency = Math.min(this.minLatency, other.minLatency);
        this.maxLatency = Math.max(this.maxLatency, other.maxLatency);
        this.tDigest.add(other.tDigest);
    }

    public double getMean() {
        return totalRequests > 0 ? totalLatency / totalRequests : 0.0;
    }

    public double getVariance() {
        if (totalRequests <= 1) {
            return 0.0;
        }
        double mean = getMean();
        return (sumOfSquares - totalRequests * mean * mean) / (totalRequests - 1);
    }

    public double getStdDev() {
        return Math.sqrt(getVariance());
    }

    public double getPercentile(double percentile) {
        if (totalRequests == 0) {
            return 0.0;
        }
        return tDigest.quantile(percentile / 100.0);
    }

    public double getP50() {
        return getPercentile(50);
    }

    public double getP95() {
        return getPercentile(95);
    }

    public double getP99() {
        return getPercentile(99);
    }

    public double getP999() {
        return getPercentile(99.9);
    }

    public double getErrorRate() {
        return totalRequests > 0 ? (errorRequests * 100.0) / totalRequests : 0.0;
    }
}

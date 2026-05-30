package com.sla.monitor.engine;

import io.micrometer.core.instrument.*;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class PrometheusMetricsCollector {

    private final MeterRegistry meterRegistry;
    private final Map<String, ServiceMetrics> serviceMetricsMap = new ConcurrentHashMap<>();
    private final SlidingWindowMetrics slidingWindowMetrics;

    public PrometheusMetricsCollector(MeterRegistry meterRegistry, SlidingWindowMetrics slidingWindowMetrics) {
        this.meterRegistry = meterRegistry;
        this.slidingWindowMetrics = slidingWindowMetrics;
    }

    public void recordRequest(String serviceName, long latencyMs, boolean success) {
        ServiceMetrics metrics = getServiceMetrics(serviceName);
        
        if (success) {
            metrics.requestsSuccessCounter.increment();
        } else {
            metrics.requestsFailureCounter.increment();
        }

        metrics.requestLatencyTimer.record(latencyMs, java.util.concurrent.TimeUnit.MILLISECONDS);
        metrics.totalRequestsGauge.increment();
        slidingWindowMetrics.recordRequest(serviceName, latencyMs, success);
    }

    public void updateAvailability(String serviceName, double availability) {
        ServiceMetrics metrics = getServiceMetrics(serviceName);
        metrics.availabilityGauge.set(availability);
    }

    public void updateErrorRate(String serviceName, double errorRate) {
        ServiceMetrics metrics = getServiceMetrics(serviceName);
        metrics.errorRateGauge.set(errorRate);
    }

    public void updateSlaAchievement(String serviceName, double achievementRate) {
        ServiceMetrics metrics = getServiceMetrics(serviceName);
        metrics.slaAchievementGauge.set(achievementRate);
    }

    private ServiceMetrics getServiceMetrics(String serviceName) {
        return serviceMetricsMap.computeIfAbsent(serviceName, this::createServiceMetrics);
    }

    private ServiceMetrics createServiceMetrics(String serviceName) {
        return new ServiceMetrics(
            Counter.builder("sla_requests_total")
                .tag("service", serviceName)
                .tag("status", "success")
                .description("Total successful requests")
                .register(meterRegistry),
            Counter.builder("sla_requests_total")
                .tag("service", serviceName)
                .tag("status", "failure")
                .description("Total failed requests")
                .register(meterRegistry),
            Timer.builder("sla_request_latency_ms")
                .tag("service", serviceName)
                .description("Request latency distribution")
                .publishPercentiles(0.5, 0.9, 0.95, 0.99)
                .register(meterRegistry),
            AtomicLongGauge.builder("sla_availability_percent")
                .tag("service", serviceName)
                .description("Service availability percentage")
                .register(meterRegistry),
            AtomicLongGauge.builder("sla_error_rate_percent")
                .tag("service", serviceName)
                .description("Error rate percentage")
                .register(meterRegistry),
            AtomicLongGauge.builder("sla_achievement_rate")
                .tag("service", serviceName)
                .description("SLA achievement rate")
                .register(meterRegistry),
            AtomicLongGauge.builder("sla_total_requests")
                .tag("service", serviceName)
                .description("Total requests count")
                .register(meterRegistry)
        );
    }

    private static class ServiceMetrics {
        final Counter requestsSuccessCounter;
        final Counter requestsFailureCounter;
        final Timer requestLatencyTimer;
        final AtomicLongGauge availabilityGauge;
        final AtomicLongGauge errorRateGauge;
        final AtomicLongGauge slaAchievementGauge;
        final AtomicLongGauge totalRequestsGauge;

        ServiceMetrics(Counter requestsSuccessCounter, Counter requestsFailureCounter,
                       Timer requestLatencyTimer, AtomicLongGauge availabilityGauge,
                       AtomicLongGauge errorRateGauge, AtomicLongGauge slaAchievementGauge,
                       AtomicLongGauge totalRequestsGauge) {
            this.requestsSuccessCounter = requestsSuccessCounter;
            this.requestsFailureCounter = requestsFailureCounter;
            this.requestLatencyTimer = requestLatencyTimer;
            this.availabilityGauge = availabilityGauge;
            this.errorRateGauge = errorRateGauge;
            this.slaAchievementGauge = slaAchievementGauge;
            this.totalRequestsGauge = totalRequestsGauge;
        }
    }

    private static class AtomicLongGauge {
        private final AtomicLong value = new AtomicLong(0);
        private final Gauge gauge;

        private AtomicLongGauge(Gauge gauge) {
            this.gauge = gauge;
        }

        public static AtomicLongGaugeBuilder builder(String name) {
            return new AtomicLongGaugeBuilder(name);
        }

        public void set(double newValue) {
            value.set((long) (newValue * 100));
        }

        public void increment() {
            value.incrementAndGet();
        }

        public static class AtomicLongGaugeBuilder {
            private final Gauge.Builder builder;

            AtomicLongGaugeBuilder(String name) {
                this.builder = Gauge.builder(name, new AtomicLong(0), AtomicLong::get);
            }

            public AtomicLongGaugeBuilder tag(String key, String value) {
                builder.tag(key, value);
                return this;
            }

            public AtomicLongGaugeBuilder description(String desc) {
                builder.description(desc);
                return this;
            }

            public AtomicLongGauge register(MeterRegistry registry) {
                AtomicLong valueHolder = new AtomicLong(0);
                Gauge gauge = builder.register(registry);
                return new AtomicLongGauge(gauge);
            }
        }
    }
}

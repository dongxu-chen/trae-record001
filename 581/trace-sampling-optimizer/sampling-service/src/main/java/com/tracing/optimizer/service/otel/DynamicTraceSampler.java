package com.tracing.optimizer.service.otel;

import com.tracing.optimizer.core.engine.SamplingOptimizer;
import com.tracing.optimizer.core.edge.EdgeSampler;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.SpanKind;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.api.trace.propagation.W3CTraceContextPropagator;
import io.opentelemetry.context.Context;
import io.opentelemetry.context.propagation.TextMapPropagator;
import io.opentelemetry.exporter.otlp.trace.OtlpGrpcSpanExporter;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.resources.Resource;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.Sampler;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;
import io.opentelemetry.sdk.trace.samplers.SamplingResult;
import io.opentelemetry.semconv.ServiceAttributes;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class DynamicTraceSampler implements Sampler {

    private static final Logger log = LoggerFactory.getLogger(DynamicTraceSampler.class);

    private final SamplingOptimizer optimizer;
    private final Map<String, Double> rateCache;
    private final double defaultRate;

    public DynamicTraceSampler(SamplingOptimizer optimizer, double defaultRate) {
        this.optimizer = optimizer;
        this.rateCache = new ConcurrentHashMap<>();
        this.defaultRate = defaultRate;
    }

    @Override
    public SamplingResult shouldSample(Context parentContext, String traceId, String name,
                                        SpanKind spanKind, Attributes attributes,
                                        java.util.List<io.opentelemetry.api.trace.SpanLink> parentLinks) {
        String serviceName = extractServiceName(attributes);
        Double rate = rateCache.computeIfAbsent(serviceName, svc -> {
            com.tracing.optimizer.core.model.SamplingRate currentRate =
                    optimizer.getCurrentRate(svc);
            return currentRate != null ? currentRate.getRate() : defaultRate;
        });

        SamplingResult.Decision decision = Math.random() < rate
                ? SamplingResult.Decision.RECORD_AND_SAMPLE
                : SamplingResult.Decision.DROP;

        log.debug("Sampling decision for service {}: rate={}, decision={}", serviceName, rate, decision);

        return SamplingResult.create(decision);
    }

    @Override
    public String getDescription() {
        return "DynamicTraceSampler{optimizer-driven}";
    }

    public void updateRate(String serviceName, double newRate) {
        rateCache.put(serviceName, newRate);
        log.info("Updated sampling rate cache for {}: {}", serviceName, newRate);
    }

    public void refreshRates() {
        Map<String, com.tracing.optimizer.core.model.SamplingRate> allRates =
                optimizer.getAllCurrentRates();
        for (Map.Entry<String, com.tracing.optimizer.core.model.SamplingRate> entry :
                allRates.entrySet()) {
            rateCache.put(entry.getKey(), entry.getValue().getRate());
        }
        log.info("Refreshed sampling rate cache with {} entries", allRates.size());
    }

    private String extractServiceName(Attributes attributes) {
        return attributes.get(ServiceAttributes.SERVICE_NAME) != null
                ? attributes.get(ServiceAttributes.SERVICE_NAME)
                : "unknown";
    }

    public static OpenTelemetrySdk buildOpenTelemetry(String serviceName, String otlpEndpoint,
                                                       SamplingOptimizer optimizer) {
        DynamicTraceSampler sampler = new DynamicTraceSampler(optimizer, 0.1);

        Resource resource = Resource.getDefault()
                .merge(Resource.create(Attributes.of(
                        ServiceAttributes.SERVICE_NAME, serviceName
                )));

        OtlpGrpcSpanExporter spanExporter = OtlpGrpcSpanExporter.builder()
                .setEndpoint(otlpEndpoint)
                .build();

        SdkTracerProvider tracerProvider = SdkTracerProvider.builder()
                .setResource(resource)
                .setSampler(sampler)
                .addSpanProcessor(BatchSpanProcessor.builder(spanExporter).build())
                .build();

        return OpenTelemetrySdk.builder()
                .setTracerProvider(tracerProvider)
                .setPropagators(W3CTraceContextPropagator.getInstance())
                .build();
    }
}

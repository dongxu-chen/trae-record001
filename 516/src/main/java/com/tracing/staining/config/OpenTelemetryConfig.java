package com.tracing.staining.config;

import com.tracing.staining.context.TraceContextHolder;
import com.tracing.staining.sampler.AdaptiveTraceSampler;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.propagation.W3CTraceContextPropagator;
import io.opentelemetry.context.propagation.ContextPropagators;
import io.opentelemetry.exporter.jaeger.JaegerGrpcSpanExporter;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.resources.Resource;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;
import io.opentelemetry.sdk.trace.sampler.Sampler;
import io.opentelemetry.sdk.trace.sampler.SamplingDecision;
import io.opentelemetry.sdk.trace.sampler.SamplingResult;
import io.opentelemetry.semconv.resource.attributes.ResourceAttributes;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import java.util.concurrent.TimeUnit;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class OpenTelemetryConfig {

    private final AdaptiveTraceSampler adaptiveTraceSampler;

    @Value("${spring.application.name:trace-staining-service}")
    private String serviceName;

    @Value("${tracing.jaeger.endpoint:http://localhost:14250}")
    private String jaegerEndpoint;

    @Value("${tracing.jaeger.enabled:true}")
    private boolean jaegerEnabled;

    @Bean
    @Primary
    public Sampler adaptiveOtelSampler() {
        return new Sampler() {
            @Override
            public SamplingResult shouldSample(
                    io.opentelemetry.context.Context parentContext,
                    String traceId,
                    String name,
                    io.opentelemetry.api.trace.SpanKind spanKind,
                    io.opentelemetry.api.common.Attributes attributes,
                    java.util.List<io.opentelemetry.api.trace.Link> parentLinks) {

                double currentRate = adaptiveTraceSampler.getCurrentSampleRate();
                boolean isStained = com.tracing.staining.context.TraceContextHolder.isStainingEnabled();

                if (isStained) {
                    return SamplingResult.create(SamplingDecision.RECORD_AND_SAMPLE);
                }

                if (currentRate >= 1.0) {
                    return SamplingResult.create(SamplingDecision.RECORD_AND_SAMPLE);
                }

                if (currentRate <= 0) {
                    return SamplingResult.create(SamplingDecision.DROP);
                }

                long traceIdHigh = Long.parseUnsignedLong(traceId.substring(0, 16), 16);
                double ratio = (double) (traceIdHigh & 0xFFFFFFFFL) / 0xFFFFFFFFL;

                if (ratio < currentRate) {
                    return SamplingResult.create(SamplingDecision.RECORD_AND_SAMPLE);
                } else {
                    return SamplingResult.create(SamplingDecision.DROP);
                }
            }

            @Override
            public String getDescription() {
                return String.format("AdaptiveSampler{currentRate=%.2f}",
                        adaptiveTraceSampler.getCurrentSampleRate());
            }
        };
    }

    @Bean
    public OpenTelemetry openTelemetry(Sampler adaptiveOtelSampler) {
        Resource resource = Resource.getDefault()
                .merge(Resource.create(
                        Attributes.builder()
                                .put(ResourceAttributes.SERVICE_NAME, serviceName)
                                .put(ResourceAttributes.SERVICE_VERSION, "1.0.0")
                                .build()
                ));

        SdkTracerProvider.SdkTracerProviderBuilder tracerProviderBuilder = SdkTracerProvider.builder()
                .setResource(resource)
                .setSampler(adaptiveOtelSampler);

        if (jaegerEnabled) {
            JaegerGrpcSpanExporter jaegerExporter = JaegerGrpcSpanExporter.builder()
                    .setEndpoint(jaegerEndpoint)
                    .setTimeout(30, TimeUnit.SECONDS)
                    .build();

            tracerProviderBuilder.addSpanProcessor(
                    BatchSpanProcessor.builder(jaegerExporter)
                            .setScheduleDelay(100, TimeUnit.MILLISECONDS)
                            .setMaxQueueSize(2048)
                            .setMaxExportBatchSize(512)
                            .build()
            );

            log.info("Jaeger exporter enabled, endpoint: {}", jaegerEndpoint);
        } else {
            log.warn("Jaeger exporter is disabled");
        }

        SdkTracerProvider tracerProvider = tracerProviderBuilder.build();

        OpenTelemetrySdk openTelemetry = OpenTelemetrySdk.builder()
                .setTracerProvider(tracerProvider)
                .setPropagators(ContextPropagators.create(W3CTraceContextPropagator.getInstance()))
                .buildAndRegisterGlobal();

        TraceContextHolder.setOpenTelemetry(openTelemetry);

        Runtime.getRuntime().addShutdownHook(new Thread(tracerProvider::close));

        log.info("OpenTelemetry initialized with adaptive sampler for service: {}", serviceName);
        return openTelemetry;
    }
}

package com.tracing.sampling.config;

import com.tracing.sampling.sampler.IntelligentAdaptiveSampler;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.api.trace.propagation.W3CTraceContextPropagator;
import io.opentelemetry.context.propagation.ContextPropagators;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.resources.Resource;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;
import io.opentelemetry.exporter.otlp.trace.OtlpGrpcSpanExporter;
import io.opentelemetry.semconv.ResourceAttributes;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.TimeUnit;

@Configuration
public class OpenTelemetryConfig {

    private final TracingProperties tracingProperties;
    private final IntelligentAdaptiveSampler intelligentAdaptiveSampler;

    public OpenTelemetryConfig(TracingProperties tracingProperties, 
                               IntelligentAdaptiveSampler intelligentAdaptiveSampler) {
        this.tracingProperties = tracingProperties;
        this.intelligentAdaptiveSampler = intelligentAdaptiveSampler;
    }

    @Bean
    public OpenTelemetry openTelemetry() {
        Resource resource = Resource.getDefault()
                .merge(Resource.create(
                        Attributes.builder()
                                .put(ResourceAttributes.SERVICE_NAME, tracingProperties.getService().getName())
                                .put("service.importance", tracingProperties.getService().getImportance().name())
                                .build()
                ));

        SdkTracerProvider tracerProvider = SdkTracerProvider.builder()
                .setSampler(intelligentAdaptiveSampler)
                .addSpanProcessor(batchSpanProcessor())
                .setResource(resource)
                .build();

        Runtime.getRuntime().addShutdownHook(new Thread(tracerProvider::close));

        return OpenTelemetrySdk.builder()
                .setTracerProvider(tracerProvider)
                .setPropagators(ContextPropagators.create(W3CTraceContextPropagator.getInstance()))
                .buildAndRegisterGlobal();
    }

    private BatchSpanProcessor batchSpanProcessor() {
        OtlpGrpcSpanExporter otlpExporter = OtlpGrpcSpanExporter.builder()
                .setEndpoint(tracingProperties.getOtlp().getEndpoint())
                .setTimeout(tracingProperties.getOtlp().getTimeoutMs(), TimeUnit.MILLISECONDS)
                .build();

        return BatchSpanProcessor.builder(otlpExporter)
                .setScheduleDelay(5000, TimeUnit.MILLISECONDS)
                .setMaxQueueSize(2048)
                .setMaxExportBatchSize(512)
                .build();
    }

    @Bean
    public Tracer tracer(OpenTelemetry openTelemetry) {
        return openTelemetry.getTracer(tracingProperties.getService().getName(), "1.0.0");
    }
}

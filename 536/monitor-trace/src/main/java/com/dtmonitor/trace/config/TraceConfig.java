package com.dtmonitor.trace.config;

import brave.Tracing;
import brave.sampler.Sampler;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import zipkin2.reporter.AsyncReporter;
import zipkin2.reporter.okhttp3.OkHttpSender;

@Configuration
public class TraceConfig {

    @Value("${zipkin.base-url:http://localhost:9411}")
    private String zipkinBaseUrl;

    @Value("${spring.application.name:dt-monitor}")
    private String appName;

    @Bean
    public OkHttpSender zipkinSender() {
        return OkHttpSender.create(zipkinBaseUrl + "/api/v2/spans");
    }

    @Bean
    public AsyncReporter<zipkin2.Span> zipkinReporter(OkHttpSender sender) {
        return AsyncReporter.create(sender);
    }

    @Bean
    public Tracing tracing(AsyncReporter<zipkin2.Span> reporter) {
        return Tracing.newBuilder()
                .localServiceName(appName)
                .spanReporter(reporter)
                .sampler(Sampler.ALWAYS_SAMPLE)
                .build();
    }
}

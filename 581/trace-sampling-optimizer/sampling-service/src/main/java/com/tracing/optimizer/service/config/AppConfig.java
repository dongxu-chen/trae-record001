package com.tracing.optimizer.service.config;

import com.tracing.optimizer.core.cost.CostModel;
import com.tracing.optimizer.core.engine.SamplingOptimizer;
import com.tracing.optimizer.core.model.CostBudget;
import com.tracing.optimizer.service.otel.DynamicTraceSampler;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

@Configuration
@EnableScheduling
public class AppConfig {

    @Value("${sampling.cost.daily-budget-usd:100.0}")
    private double dailyBudgetUsd;

    @Value("${sampling.cost.per-span:0.00001}")
    private double costPerSpan;

    @Value("${sampling.cost.per-span-storage:0.000005}")
    private double costPerSpanStorage;

    @Value("${sampling.cost.per-span-network:0.000003}")
    private double costPerSpanNetwork;

    @Value("${sampling.cost.per-span-compute:0.000002}")
    private double costPerSpanCompute;

    @Value("${sampling.cost.alert-threshold-percent:80.0}")
    private double alertThresholdPercent;

    @Value("${otel.exporter.otlp.endpoint:http://localhost:4317}")
    private String otlpEndpoint;

    @Value("${spring.application.name:trace-sampling-optimizer}")
    private String serviceName;

    @Bean
    public CostBudget costBudget() {
        CostBudget budget = new CostBudget(dailyBudgetUsd, costPerSpan);
        budget.setCostPerSpanStorage(costPerSpanStorage);
        budget.setCostPerSpanNetwork(costPerSpanNetwork);
        budget.setCostPerSpanCompute(costPerSpanCompute);
        budget.setAlertThresholdPercent(alertThresholdPercent);
        return budget;
    }

    @Bean
    public CostModel costModel(CostBudget budget) {
        CostModel model = new CostModel(budget);
        return model;
    }

    @Bean
    public SamplingOptimizer samplingOptimizer(CostModel costModel) {
        SamplingOptimizer optimizer = new SamplingOptimizer(costModel);
        optimizer.initialize();
        return optimizer;
    }

    @Bean
    public OpenTelemetrySdk openTelemetrySdk(SamplingOptimizer optimizer) {
        return DynamicTraceSampler.buildOpenTelemetry(serviceName, otlpEndpoint, optimizer);
    }
}

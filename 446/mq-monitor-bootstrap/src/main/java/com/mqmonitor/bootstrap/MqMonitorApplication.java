package com.mqmonitor.bootstrap;

import com.mqmonitor.alert.AlertManager;
import com.mqmonitor.common.config.AlertConfig;
import com.mqmonitor.common.config.MQClusterConfig;
import com.mqmonitor.common.config.PredictionConfig;
import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.collector.MetricsManager;
import com.mqmonitor.exporter.PrometheusExporter;
import com.mqmonitor.prediction.PredictionManager;
import io.micrometer.prometheus.PrometheusMeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;

import java.util.ArrayList;
import java.util.List;

@SpringBootApplication(scanBasePackages = {"com.mqmonitor.api", "com.mqmonitor.bootstrap"})
@EnableScheduling
public class MqMonitorApplication {
    private static final Logger logger = LoggerFactory.getLogger(MqMonitorApplication.class);

    private MetricsManager metricsManager;
    private AlertManager alertManager;
    private PredictionManager predictionManager;
    private PrometheusExporter prometheusExporter;

    public static void main(String[] args) {
        SpringApplication.run(MqMonitorApplication.class, args);
    }

    @Bean
    public MetricsManager metricsManager() {
        metricsManager = MetricsManager.getInstance();

        List<MQClusterConfig> clusterConfigs = new ArrayList<>();

        MQClusterConfig kafkaConfig = new MQClusterConfig();
        kafkaConfig.setMqType(MQType.KAFKA);
        kafkaConfig.setClusterName("kafka-main");
        kafkaConfig.setBootstrapServers("localhost:9092");
        kafkaConfig.setPollIntervalMs(5000);
        clusterConfigs.add(kafkaConfig);

        MQClusterConfig rabbitConfig = new MQClusterConfig();
        rabbitConfig.setMqType(MQType.RABBITMQ);
        rabbitConfig.setClusterName("rabbitmq-main");
        rabbitConfig.setHost("localhost");
        rabbitConfig.setPort(5672);
        rabbitConfig.setVirtualHost("/");
        rabbitConfig.setUsername("guest");
        rabbitConfig.setPassword("guest");
        clusterConfigs.add(rabbitConfig);

        MQClusterConfig rocketConfig = new MQClusterConfig();
        rocketConfig.setMqType(MQType.ROCKETMQ);
        rocketConfig.setClusterName("rocketmq-main");
        rocketConfig.setNameServer("localhost:9876");
        clusterConfigs.add(rocketConfig);

        metricsManager.initialize(clusterConfigs, 5000);
        logger.info("MetricsManager initialized with {} clusters", clusterConfigs.size());

        return metricsManager;
    }

    @Bean
    public AlertManager alertManager(MetricsManager metricsManager) {
        AlertConfig alertConfig = metricsManager.getAlertConfig();
        alertConfig.setLatencyThresholdMs(3000);
        alertConfig.setBacklogThreshold(5000);
        alertConfig.setConsumerLagThreshold(3000);
        alertConfig.setAnomalyZScoreThreshold(2.5);
        alertConfig.setThroughputDropThresholdPercent(25.0);

        alertManager = AlertManager.getInstance(alertConfig);
        alertManager.startDetection(10000);
        logger.info("AlertManager started");

        return alertManager;
    }

    @Bean
    public PredictionManager predictionManager(MetricsManager metricsManager) {
        PredictionConfig predictionConfig = metricsManager.getPredictionConfig();
        predictionConfig.setPredictionHorizonMinutes(30);
        predictionConfig.setMinDataPointsForPrediction(20);
        predictionConfig.setDefaultAlgorithm("HOLT_WINTERS");
        predictionConfig.setBacklogWarningThreshold(10000);

        predictionManager = PredictionManager.getInstance(predictionConfig);
        logger.info("PredictionManager initialized");

        return predictionManager;
    }

    @Bean
    public PrometheusExporter prometheusExporter(PrometheusMeterRegistry registry) {
        prometheusExporter = new PrometheusExporter();
        prometheusExporter.startExport(5000);
        logger.info("PrometheusExporter started");

        return prometheusExporter;
    }

    @Bean
    public PrometheusMeterRegistry prometheusMeterRegistry() {
        return new PrometheusMeterRegistry(io.micrometer.prometheus.PrometheusConfig.DEFAULT);
    }
}

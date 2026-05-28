package com.mqmonitor.alert;

import com.mqmonitor.common.config.AlertConfig;
import com.mqmonitor.common.model.Alert;
import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.collector.MetricsManager;

import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class AlertManager {
    private static AlertManager instance;
    private final AnomalyDetector anomalyDetector;
    private final MetricsManager metricsManager;
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);

    private AlertManager(AlertConfig alertConfig) {
        this.metricsManager = MetricsManager.getInstance();
        this.anomalyDetector = new AnomalyDetector(alertConfig);
    }

    public static synchronized AlertManager getInstance(AlertConfig alertConfig) {
        if (instance == null) {
            instance = new AlertManager(alertConfig);
        }
        return instance;
    }

    public void startDetection(long intervalMs) {
        scheduler.scheduleAtFixedRate(this::runDetection, 5000, intervalMs, TimeUnit.MILLISECONDS);
    }

    public List<Alert> runDetection() {
        List<QueueMetrics> metrics = metricsManager.getAllMetrics();
        return anomalyDetector.detectAnomalies(metrics);
    }

    public List<Alert> getActiveAlerts() {
        return anomalyDetector.getActiveAlerts();
    }

    public List<Alert> getAllAlerts() {
        return anomalyDetector.getAllAlerts();
    }

    public AnomalyDetector getAnomalyDetector() {
        return anomalyDetector;
    }

    public void shutdown() {
        scheduler.shutdown();
    }
}

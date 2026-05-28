package com.mqmonitor.alert;

import com.mqmonitor.common.config.AlertConfig;
import com.mqmonitor.common.model.Alert;
import com.mqmonitor.common.util.JsonUtil;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class AlertNotifier {
    private static final Logger logger = LoggerFactory.getLogger(AlertNotifier.class);
    private static final MediaType JSON = MediaType.parse("application/json; charset=utf-8");

    private final AlertConfig config;
    private final OkHttpClient httpClient;

    public AlertNotifier(AlertConfig config) {
        this.config = config;
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(10, TimeUnit.SECONDS)
                .writeTimeout(10, TimeUnit.SECONDS)
                .build();
    }

    public void sendAlert(Alert alert) {
        logger.warn("ALERT TRIGGERED: [{}] {} - {}", alert.getLevel(), alert.getType(), alert.getMessage());

        if (config.isWebhookEnabled() && config.getWebhookUrl() != null) {
            sendWebhookAlert(alert);
        }

        logAlert(alert);
    }

    private void sendWebhookAlert(Alert alert) {
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("alertId", alert.getId());
            payload.put("type", alert.getType().name());
            payload.put("level", alert.getLevel().name());
            payload.put("mqType", alert.getMqType() != null ? alert.getMqType().name() : null);
            payload.put("clusterName", alert.getClusterName());
            payload.put("topic", alert.getTopic());
            payload.put("consumerGroup", alert.getConsumerGroup());
            payload.put("message", alert.getMessage());
            payload.put("details", alert.getDetails());
            payload.put("timestamp", alert.getTimestamp());

            String json = JsonUtil.toJson(payload);
            RequestBody body = RequestBody.create(json, JSON);

            Request request = new Request.Builder()
                    .url(config.getWebhookUrl())
                    .post(body)
                    .addHeader("Content-Type", "application/json")
                    .build();

            httpClient.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    logger.error("Failed to send webhook alert", e);
                }

                @Override
                public void onResponse(Call call, Response response) throws IOException {
                    if (!response.isSuccessful()) {
                        logger.error("Webhook alert returned non-success status: {}", response.code());
                    }
                    response.close();
                }
            });
        } catch (Exception e) {
            logger.error("Error sending webhook alert", e);
        }
    }

    private void logAlert(Alert alert) {
        String details = alert.getDetails() != null ? JsonUtil.toJson(alert.getDetails()) : "{}";
        logger.info("Alert details: id={}, type={}, level={}, details={}",
                alert.getId(), alert.getType(), alert.getLevel(), details);
    }
}

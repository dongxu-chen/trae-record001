package com.loganalytics.sink;

import com.loganalytics.model.AlertEvent;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AlertSink extends RichSinkFunction<AlertEvent> {
    private static final Logger LOG = LoggerFactory.getLogger(AlertSink.class);

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
    }

    @Override
    public void invoke(AlertEvent alert, Context context) throws Exception {
        String logMessage = String.format(
                "[%s] ALERT [%s] %s - %s (current: %.2f, threshold: %.2f)",
                alert.getSeverity(),
                alert.getAlertType(),
                alert.getMessage(),
                alert.getDimension() + ":" + alert.getValue(),
                alert.getCurrentValue(),
                alert.getThreshold()
        );

        switch (alert.getSeverity()) {
            case "CRITICAL":
                LOG.error(logMessage);
                break;
            case "WARNING":
                LOG.warn(logMessage);
                break;
            default:
                LOG.info(logMessage);
        }
    }

    @Override
    public void close() throws Exception {
        super.close();
    }
}

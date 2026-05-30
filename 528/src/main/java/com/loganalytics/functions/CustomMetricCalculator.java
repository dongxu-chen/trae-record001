package com.loganalytics.functions;

import com.loganalytics.model.CustomMetric;
import com.loganalytics.model.MetricsResult;
import org.apache.flink.streaming.api.functions.FlatMapFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class CustomMetricCalculator implements FlatMapFunction<MetricsResult, CustomMetric> {

    private static final Logger LOG = LoggerFactory.getLogger(CustomMetricCalculator.class);

    private final List<MetricDefinition> definitions;

    public CustomMetricCalculator(List<MetricDefinition> definitions) {
        this.definitions = definitions;
    }

    public CustomMetricCalculator() {
        this.definitions = new ArrayList<>();
    }

    @Override
    public void flatMap(MetricsResult metrics, Collector<CustomMetric> out) throws Exception {
        Map<String, Double> variables = ExpressionEngine.buildVariablesFromMetrics(metrics);

        for (MetricDefinition def : definitions) {
            try {
                double result = def.getEngine().evaluate(variables);

                if (Double.isNaN(result) || Double.isInfinite(result)) {
                    continue;
                }

                Map<String, Double> usedVars = new LinkedHashMap<>();
                for (String varName : def.getEngine().getRequiredVariables()) {
                    if (variables.containsKey(varName)) {
                        usedVars.put(varName, variables.get(varName));
                    }
                }

                CustomMetric customMetric = CustomMetric.builder()
                        .metricName(def.getName())
                        .expression(def.getExpression())
                        .dimension(metrics.getDimension())
                        .value(metrics.getValue())
                        .result(result)
                        .variables(usedVars)
                        .timestamp(System.currentTimeMillis())
                        .build();

                out.collect(customMetric);
            } catch (Exception e) {
                LOG.warn("Failed to evaluate custom metric '{}' with expression '{}': {}",
                        def.getName(), def.getExpression(), e.getMessage());
            }
        }
    }

    public static class MetricDefinition implements java.io.Serializable {
        private final String name;
        private final String expression;
        private final transient ExpressionEngine engine;

        public MetricDefinition(String name, String expression) {
            this.name = name;
            this.expression = expression;
            this.engine = new ExpressionEngine(expression);
        }

        public String getName() {
            return name;
        }

        public String getExpression() {
            return expression;
        }

        public ExpressionEngine getEngine() {
            return engine;
        }
    }

    public static List<MetricDefinition> parseDefinitions(String config) {
        List<MetricDefinition> definitions = new ArrayList<>();
        if (config == null || config.isEmpty()) {
            return definitions;
        }

        String[] entries = config.split(";");
        for (String entry : entries) {
            String[] parts = entry.split("=", 2);
            if (parts.length == 2) {
                String name = parts[0].trim();
                String expression = parts[1].trim();
                if (!name.isEmpty() && !expression.isEmpty()) {
                    definitions.add(new MetricDefinition(name, expression));
                }
            }
        }
        return definitions;
    }
}

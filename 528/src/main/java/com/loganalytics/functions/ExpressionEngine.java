package com.loganalytics.functions;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

public class ExpressionEngine {

    private final String expression;
    private final String[] tokens;

    public ExpressionEngine(String expression) {
        this.expression = expression.replaceAll("\\s+", "");
        this.tokens = tokenize(this.expression);
    }

    public double evaluate(Map<String, Double> variables) {
        return parseExpression(new TokenCursor(tokens), variables);
    }

    public String[] getRequiredVariables() {
        return tokens;
    }

    public String getExpression() {
        return expression;
    }

    private String[] tokenize(String expr) {
        java.util.List<String> tokenList = new java.util.ArrayList<>();
        StringBuilder current = new StringBuilder();

        for (int i = 0; i < expr.length(); i++) {
            char c = expr.charAt(i);
            if (isOperator(c) || c == '(' || c == ')') {
                if (current.length() > 0) {
                    tokenList.add(current.toString());
                    current = new StringBuilder();
                }
                tokenList.add(String.valueOf(c));
            } else if (Character.isLetterOrDigit(c) || c == '_' || c == '.') {
                current.append(c);
            } else if (c == '-' && (tokenList.isEmpty() || isOperatorOrParen(tokenList.get(tokenList.size() - 1)))) {
                current.append(c);
            }
        }
        if (current.length() > 0) {
            tokenList.add(current.toString());
        }

        return tokenList.toArray(new String[0]);
    }

    private boolean isOperator(char c) {
        return c == '+' || c == '-' || c == '*' || c == '/';
    }

    private boolean isOperatorOrParen(String token) {
        return token.length() == 1 && (isOperator(token.charAt(0)) || token.equals("(") || token.equals(")"));
    }

    private double parseExpression(TokenCursor cursor, Map<String, Double> variables) {
        double result = parseTerm(cursor, variables);
        while (cursor.hasNext() && (cursor.peek().equals("+") || cursor.peek().equals("-"))) {
            String op = cursor.next();
            double term = parseTerm(cursor, variables);
            if (op.equals("+")) {
                result += term;
            } else {
                result -= term;
            }
        }
        return result;
    }

    private double parseTerm(TokenCursor cursor, Map<String, Double> variables) {
        double result = parseFactor(cursor, variables);
        while (cursor.hasNext() && (cursor.peek().equals("*") || cursor.peek().equals("/"))) {
            String op = cursor.next();
            double factor = parseFactor(cursor, variables);
            if (op.equals("*")) {
                result *= factor;
            } else {
                if (factor == 0) {
                    result = 0;
                } else {
                    result /= factor;
                }
            }
        }
        return result;
    }

    private double parseFactor(TokenCursor cursor, Map<String, Double> variables) {
        if (cursor.peek().equals("(")) {
            cursor.next();
            double result = parseExpression(cursor, variables);
            if (cursor.hasNext() && cursor.peek().equals(")")) {
                cursor.next();
            }
            return result;
        }

        String token = cursor.next();
        Double value = resolveVariable(token, variables);
        if (value != null) {
            return value;
        }

        try {
            return Double.parseDouble(token);
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }

    private Double resolveVariable(String token, Map<String, Double> variables) {
        if (variables.containsKey(token)) {
            return variables.get(token);
        }

        String snakeCase = camelToSnake(token);
        if (variables.containsKey(snakeCase)) {
            return variables.get(snakeCase);
        }

        String camelCase = snakeToCamel(snakeCase);
        if (variables.containsKey(camelCase)) {
            return variables.get(camelCase);
        }

        return null;
    }

    private String camelToSnake(String str) {
        return str.replaceAll("([a-z])([A-Z])", "$1_$2").toLowerCase();
    }

    private String snakeToCamel(String str) {
        StringBuilder result = new StringBuilder();
        boolean nextUpper = false;
        for (char c : str.toCharArray()) {
            if (c == '_') {
                nextUpper = true;
            } else {
                if (nextUpper) {
                    result.append(Character.toUpperCase(c));
                    nextUpper = false;
                } else {
                    result.append(c);
                }
            }
        }
        return result.toString();
    }

    public static Map<String, Double> buildVariablesFromMetrics(
            com.loganalytics.model.MetricsResult metrics) {
        Map<String, Double> vars = new LinkedHashMap<>();
        vars.put("total_requests", (double) metrics.getTotalRequests());
        vars.put("error_requests", (double) metrics.getErrorRequests());
        vars.put("error_rate", metrics.getErrorRate());
        vars.put("qps", metrics.getQps());
        vars.put("avg_latency", metrics.getAvgLatency());
        vars.put("min_latency", metrics.getMinLatency());
        vars.put("max_latency", metrics.getMaxLatency());
        vars.put("stddev_latency", metrics.getStdDevLatency());
        vars.put("variance", metrics.getVariance());
        vars.put("p50_latency", metrics.getP50Latency());
        vars.put("p95_latency", metrics.getP95Latency());
        vars.put("p99_latency", metrics.getP99Latency());
        vars.put("p999_latency", metrics.getP999Latency());
        vars.put("error_rate_mean", metrics.getErrorRateMean());
        vars.put("error_rate_stddev", metrics.getErrorRateStdDev());
        vars.put("latency_mean", metrics.getLatencyMean());
        vars.put("latency_stddev", metrics.getLatencyStdDev());
        vars.put("qps_mean", metrics.getQpsMean());
        vars.put("qps_stddev", metrics.getQpsStdDev());

        vars.put("latency_range", metrics.getMaxLatency() - metrics.getMinLatency());
        vars.put("error_burst_score", metrics.getErrorRate() * metrics.getQps() / 100.0);
        vars.put("latency_cv", metrics.getAvgLatency() > 0
                ? metrics.getStdDevLatency() / metrics.getAvgLatency() : 0.0);
        vars.put("tail_ratio", metrics.getP50Latency() > 0
                ? metrics.getP99Latency() / metrics.getP50Latency() : 0.0);
        vars.put("upstream_overhead", metrics.getP99Latency() - metrics.getP50Latency());

        return vars;
    }

    private static class TokenCursor {
        private final String[] tokens;
        private int pos = 0;

        TokenCursor(String[] tokens) {
            this.tokens = tokens;
        }

        boolean hasNext() {
            return pos < tokens.length;
        }

        String peek() {
            return hasNext() ? tokens[pos] : "";
        }

        String next() {
            return hasNext() ? tokens[pos++] : "";
        }
    }
}

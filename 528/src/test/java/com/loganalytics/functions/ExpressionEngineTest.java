package com.loganalytics.functions;

import com.loganalytics.model.CustomMetric;
import com.loganalytics.model.MetricsResult;
import org.apache.flink.util.Collector;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

public class ExpressionEngineTest {

    @Test
    public void testSimpleArithmetic() {
        ExpressionEngine engine = new ExpressionEngine("a+b");
        java.util.Map<String, Double> vars = new java.util.HashMap<>();
        vars.put("a", 10.0);
        vars.put("b", 20.0);
        assertEquals(30.0, engine.evaluate(vars), 0.01);
    }

    @Test
    public void testMultiplicationAndDivision() {
        ExpressionEngine engine = new ExpressionEngine("a*b/c");
        java.util.Map<String, Double> vars = new java.util.HashMap<>();
        vars.put("a", 10.0);
        vars.put("b", 5.0);
        vars.put("c", 2.0);
        assertEquals(25.0, engine.evaluate(vars), 0.01);
    }

    @Test
    public void testParentheses() {
        ExpressionEngine engine = new ExpressionEngine("(a+b)*c");
        java.util.Map<String, Double> vars = new java.util.HashMap<>();
        vars.put("a", 10.0);
        vars.put("b", 5.0);
        vars.put("c", 3.0);
        assertEquals(45.0, engine.evaluate(vars), 0.01);
    }

    @Test
    public void testComplexExpression() {
        ExpressionEngine engine = new ExpressionEngine("error_rate*qps/100");
        java.util.Map<String, Double> vars = new java.util.HashMap<>();
        vars.put("error_rate", 5.0);
        vars.put("qps", 1000.0);
        assertEquals(50.0, engine.evaluate(vars), 0.01);
    }

    @Test
    public void testSnakeCaseResolution() {
        ExpressionEngine engine = new ExpressionEngine("p99_latency/p50_latency");
        java.util.Map<String, Double> vars = new java.util.HashMap<>();
        vars.put("p99_latency", 200.0);
        vars.put("p50_latency", 50.0);
        assertEquals(4.0, engine.evaluate(vars), 0.01);
    }

    @Test
    public void testDivisionByZero() {
        ExpressionEngine engine = new ExpressionEngine("a/b");
        java.util.Map<String, Double> vars = new java.util.HashMap<>();
        vars.put("a", 100.0);
        vars.put("b", 0.0);
        assertEquals(0.0, engine.evaluate(vars), 0.01);
    }

    @Test
    public void testMissingVariable() {
        ExpressionEngine engine = new ExpressionEngine("a+b");
        java.util.Map<String, Double> vars = new java.util.HashMap<>();
        vars.put("a", 10.0);
        double result = engine.evaluate(vars);
        assertEquals(10.0, result, 0.01);
    }

    @Test
    public void testBuildVariablesFromMetrics() {
        MetricsResult metrics = MetricsResult.builder()
                .errorRate(5.0)
                .qps(1000.0)
                .p50Latency(50.0)
                .p99Latency(200.0)
                .avgLatency(100.0)
                .stdDevLatency(30.0)
                .minLatency(10.0)
                .maxLatency(300.0)
                .build();

        java.util.Map<String, Double> vars = ExpressionEngine.buildVariablesFromMetrics(metrics);

        assertEquals(5.0, vars.get("error_rate"), 0.01);
        assertEquals(1000.0, vars.get("qps"), 0.01);
        assertEquals(50.0, vars.get("p50_latency"), 0.01);
        assertEquals(200.0, vars.get("p99_latency"), 0.01);
        assertEquals(290.0, vars.get("latency_range"), 0.01);
        assertEquals(0.3, vars.get("latency_cv"), 0.01);
        assertEquals(4.0, vars.get("tail_ratio"), 0.01);
    }
}

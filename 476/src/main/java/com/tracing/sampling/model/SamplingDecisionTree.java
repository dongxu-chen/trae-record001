package com.tracing.sampling.model;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class SamplingDecisionTree {
    
    private String traceId;
    private String spanName;
    private long timestamp;
    private boolean finalDecision;
    private String finalReason;
    private double finalSampleRate;
    private DecisionTreeNode root;
    private List<DecisionStep> decisionSteps;
    private Map<String, Object> inputParameters;
    private Map<String, Object> factors;

    public SamplingDecisionTree() {
        this.decisionSteps = new ArrayList<>();
        this.inputParameters = new HashMap<>();
        this.factors = new HashMap<>();
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getSpanName() {
        return spanName;
    }

    public void setSpanName(String spanName) {
        this.spanName = spanName;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    public boolean isFinalDecision() {
        return finalDecision;
    }

    public void setFinalDecision(boolean finalDecision) {
        this.finalDecision = finalDecision;
    }

    public String getFinalReason() {
        return finalReason;
    }

    public void setFinalReason(String finalReason) {
        this.finalReason = finalReason;
    }

    public double getFinalSampleRate() {
        return finalSampleRate;
    }

    public void setFinalSampleRate(double finalSampleRate) {
        this.finalSampleRate = finalSampleRate;
    }

    public DecisionTreeNode getRoot() {
        return root;
    }

    public void setRoot(DecisionTreeNode root) {
        this.root = root;
    }

    public List<DecisionStep> getDecisionSteps() {
        return decisionSteps;
    }

    public void setDecisionSteps(List<DecisionStep> decisionSteps) {
        this.decisionSteps = decisionSteps;
    }

    public void addDecisionStep(DecisionStep step) {
        this.decisionSteps.add(step);
    }

    public Map<String, Object> getInputParameters() {
        return inputParameters;
    }

    public void setInputParameters(Map<String, Object> inputParameters) {
        this.inputParameters = inputParameters;
    }

    public void addInputParameter(String key, Object value) {
        this.inputParameters.put(key, value);
    }

    public Map<String, Object> getFactors() {
        return factors;
    }

    public void setFactors(Map<String, Object> factors) {
        this.factors = factors;
    }

    public void addFactor(String key, Object value) {
        this.factors.put(key, value);
    }

    public static class DecisionStep {
        private int stepNumber;
        private String stepName;
        private String description;
        private boolean passed;
        private String result;
        private Map<String, Object> details;

        public DecisionStep() {
            this.details = new HashMap<>();
        }

        public DecisionStep(int stepNumber, String stepName, String description, boolean passed, String result) {
            this.stepNumber = stepNumber;
            this.stepName = stepName;
            this.description = description;
            this.passed = passed;
            this.result = result;
            this.details = new HashMap<>();
        }

        public int getStepNumber() {
            return stepNumber;
        }

        public void setStepNumber(int stepNumber) {
            this.stepNumber = stepNumber;
        }

        public String getStepName() {
            return stepName;
        }

        public void setStepName(String stepName) {
            this.stepName = stepName;
        }

        public String getDescription() {
            return description;
        }

        public void setDescription(String description) {
            this.description = description;
        }

        public boolean isPassed() {
            return passed;
        }

        public void setPassed(boolean passed) {
            this.passed = passed;
        }

        public String getResult() {
            return result;
        }

        public void setResult(String result) {
            this.result = result;
        }

        public Map<String, Object> getDetails() {
            return details;
        }

        public void setDetails(Map<String, Object> details) {
            this.details = details;
        }

        public void addDetail(String key, Object value) {
            this.details.put(key, value);
        }
    }
}

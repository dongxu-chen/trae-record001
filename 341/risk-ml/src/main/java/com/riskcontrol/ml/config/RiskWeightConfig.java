package com.riskcontrol.ml.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.HashMap;
import java.util.Map;

@Configuration
@ConfigurationProperties(prefix = "riskcontrol.weights")
public class RiskWeightConfig {

    private double ruleWeight = 0.6;
    private double mlWeight = 0.4;
    private double highRiskConservationFactor = 0.9;
    private int highRiskThreshold = 70;

    private Map<String, SceneWeight> sceneWeights = new HashMap<>();

    public RiskWeightConfig() {
        sceneWeights.put("login", new SceneWeight(0.55, 0.45, 70, 0.9));
        sceneWeights.put("register", new SceneWeight(0.7, 0.3, 60, 0.85));
        sceneWeights.put("password_change", new SceneWeight(0.5, 0.5, 75, 0.95));
        sceneWeights.put("sensitive_operation", new SceneWeight(0.4, 0.6, 65, 0.95));
    }

    public double getRuleWeight() {
        return ruleWeight;
    }

    public void setRuleWeight(double ruleWeight) {
        this.ruleWeight = ruleWeight;
    }

    public double getMlWeight() {
        return mlWeight;
    }

    public void setMlWeight(double mlWeight) {
        this.mlWeight = mlWeight;
    }

    public double getHighRiskConservationFactor() {
        return highRiskConservationFactor;
    }

    public void setHighRiskConservationFactor(double highRiskConservationFactor) {
        this.highRiskConservationFactor = highRiskConservationFactor;
    }

    public int getHighRiskThreshold() {
        return highRiskThreshold;
    }

    public void setHighRiskThreshold(int highRiskThreshold) {
        this.highRiskThreshold = highRiskThreshold;
    }

    public Map<String, SceneWeight> getSceneWeights() {
        return sceneWeights;
    }

    public void setSceneWeights(Map<String, SceneWeight> sceneWeights) {
        this.sceneWeights = sceneWeights;
    }

    public SceneWeight getSceneWeight(String scene) {
        SceneWeight weight = sceneWeights.get(scene);
        if (weight == null) {
            weight = new SceneWeight(ruleWeight, mlWeight, highRiskThreshold, highRiskConservationFactor);
        }
        return weight;
    }

    public void updateSceneWeight(String scene, double ruleWeight, double mlWeight,
                                  int highRiskThreshold, double conservationFactor) {
        SceneWeight weight = sceneWeights.getOrDefault(scene, new SceneWeight());
        weight.setRuleWeight(ruleWeight);
        weight.setMlWeight(mlWeight);
        weight.setHighRiskThreshold(highRiskThreshold);
        weight.setConservationFactor(conservationFactor);
        sceneWeights.put(scene, weight);
    }

    public static class SceneWeight {
        private double ruleWeight;
        private double mlWeight;
        private int highRiskThreshold;
        private double conservationFactor;

        public SceneWeight() {
            this(0.6, 0.4, 70, 0.9);
        }

        public SceneWeight(double ruleWeight, double mlWeight, int highRiskThreshold, double conservationFactor) {
            this.ruleWeight = ruleWeight;
            this.mlWeight = mlWeight;
            this.highRiskThreshold = highRiskThreshold;
            this.conservationFactor = conservationFactor;
        }

        public double getRuleWeight() {
            return ruleWeight;
        }

        public void setRuleWeight(double ruleWeight) {
            this.ruleWeight = ruleWeight;
        }

        public double getMlWeight() {
            return mlWeight;
        }

        public void setMlWeight(double mlWeight) {
            this.mlWeight = mlWeight;
        }

        public int getHighRiskThreshold() {
            return highRiskThreshold;
        }

        public void setHighRiskThreshold(int highRiskThreshold) {
            this.highRiskThreshold = highRiskThreshold;
        }

        public double getConservationFactor() {
            return conservationFactor;
        }

        public void setConservationFactor(double conservationFactor) {
            this.conservationFactor = conservationFactor;
        }

        public void normalize() {
            double total = ruleWeight + mlWeight;
            if (total > 0) {
                ruleWeight = ruleWeight / total;
                mlWeight = mlWeight / total;
            }
        }
    }
}

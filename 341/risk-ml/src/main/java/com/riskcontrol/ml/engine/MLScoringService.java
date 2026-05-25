package com.riskcontrol.ml.engine;

import com.riskcontrol.common.enums.EventType;
import com.riskcontrol.common.model.FeatureVector;
import com.riskcontrol.common.model.RiskAssessmentResult;
import com.riskcontrol.common.model.RiskEvent;
import com.riskcontrol.common.model.UserBehaviorProfile;
import com.riskcontrol.ml.config.LightGBMConfig;
import com.riskcontrol.ml.config.RiskWeightConfig;
import com.riskcontrol.ml.config.RiskWeightConfig.SceneWeight;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class MLScoringService {

    private static final Logger logger = LoggerFactory.getLogger(MLScoringService.class);

    private final LightGBMModelManager modelManager;
    private final FeatureEngineeringService featureEngineeringService;
    private final LightGBMConfig config;
    private final RiskWeightConfig weightConfig;

    @Autowired
    public MLScoringService(LightGBMModelManager modelManager,
                            FeatureEngineeringService featureEngineeringService,
                            LightGBMConfig config,
                            RiskWeightConfig weightConfig) {
        this.modelManager = modelManager;
        this.featureEngineeringService = featureEngineeringService;
        this.config = config;
        this.weightConfig = weightConfig;
    }

    public RiskAssessmentResult scoreWithML(RiskEvent event,
                                            UserBehaviorProfile profile,
                                            RiskAssessmentResult currentResult) {
        long startTime = System.currentTimeMillis();

        if (!config.isMlEnabled() || !modelManager.isModelLoaded()) {
            logger.debug("ML scoring disabled or model not loaded, skipping ML prediction");
            currentResult.setMlScore(0);
            return currentResult;
        }

        try {
            FeatureVector features = featureEngineeringService.buildFeatureVector(event, profile);

            double[] featureArray = features.toArray();
            double rawPrediction = modelManager.predictSingle(featureArray);

            int mlScore = convertPredictionToScore(rawPrediction);

            currentResult.setMlScore(mlScore);
            event.setMlScore(mlScore);

            SceneWeight sceneWeight = getSceneWeight(event.getEventType());
            int finalScore = calculateCombinedScore(
                    currentResult.getRuleScore(), mlScore, currentResult.getFinalScore(), sceneWeight);
            currentResult.setFinalScore(finalScore);

            logger.info("ML scoring completed for event {}: raw={}, mlScore={}, finalScore={}, scene={}",
                    event.getEventId(), rawPrediction, mlScore, finalScore, getSceneName(event.getEventType()));

        } catch (Exception e) {
            logger.error("Error during ML scoring for event: {}", event.getEventId(), e);
            currentResult.setMlScore(0);
        }

        long processingTime = System.currentTimeMillis() - startTime;
        currentResult.setProcessingTimeMs(currentResult.getProcessingTimeMs() + processingTime);

        return currentResult;
    }

    private int convertPredictionToScore(double prediction) {
        double probability;
        if ("classification".equals(config.getModelType())) {
            probability = 1.0 / (1.0 + Math.exp(-prediction));
        } else {
            probability = Math.max(0.0, Math.min(1.0, prediction));
        }
        return (int) Math.round(probability * 100);
    }

    private int calculateCombinedScore(int ruleScore, int mlScore, int currentFinalScore, SceneWeight sceneWeight) {
        double ruleWeight = sceneWeight.getRuleWeight();
        double mlWeight = sceneWeight.getMlWeight();
        int highRiskThreshold = sceneWeight.getHighRiskThreshold();
        double conservationFactor = sceneWeight.getConservationFactor();

        int baseScore = currentFinalScore > 0 ? currentFinalScore : ruleScore;

        double combined = (baseScore * ruleWeight) + (mlScore * mlWeight);

        if (baseScore >= highRiskThreshold) {
            combined = Math.max(combined, baseScore * conservationFactor);
        }

        return (int) Math.min(Math.round(combined), 100);
    }

    private SceneWeight getSceneWeight(EventType eventType) {
        String sceneName = getSceneName(eventType);
        return weightConfig.getSceneWeight(sceneName);
    }

    private String getSceneName(EventType eventType) {
        if (eventType == null) {
            return "default";
        }
        switch (eventType) {
            case LOGIN:
                return "login";
            case REGISTER:
                return "register";
            case PASSWORD_CHANGE:
            case PASSWORD_RESET:
                return "password_change";
            case SENSITIVE_OPERATION:
                return "sensitive_operation";
            default:
                return "default";
        }
    }

    public boolean isModelReady() {
        return config.isMlEnabled() && modelManager.isModelLoaded();
    }

    public void reloadModel() throws Exception {
        modelManager.loadModel();
    }

    public SceneWeight getCurrentSceneWeight(EventType eventType) {
        return getSceneWeight(eventType);
    }

    public RiskWeightConfig getWeightConfig() {
        return weightConfig;
    }

    public void updateSceneWeight(String scene, double ruleWeight, double mlWeight,
                                  int highRiskThreshold, double conservationFactor) {
        weightConfig.updateSceneWeight(scene, ruleWeight, mlWeight, highRiskThreshold, conservationFactor);
        logger.info("Updated scene weight for {}: ruleWeight={}, mlWeight={}, threshold={}, conservation={}",
                scene, ruleWeight, mlWeight, highRiskThreshold, conservationFactor);
    }

    public FeatureVector buildFeaturesForExplanation(RiskEvent event, UserBehaviorProfile profile) {
        return featureEngineeringService.buildFeatureVector(event, profile);
    }

    public FeatureEngineeringService getFeatureEngineeringService() {
        return featureEngineeringService;
    }
}

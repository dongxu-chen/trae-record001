package com.riskcontrol.ml.engine;

import com.riskcontrol.common.model.FeatureVector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class FallbackModel {

    private static final Logger logger = LoggerFactory.getLogger(FallbackModel.class);

    private static final double[] FEATURE_WEIGHTS = {
            0.05, 0.15, 0.20, 0.10, 0.03, 0.08, 0.07, 0.10,
            0.05, 0.05, 0.02, 0.02, 0.03, 0.02, 0.01, 0.01,
            0.05, 0.10, 0.03, 0.03
    };

    public double predict(FeatureVector features) {
        double[] featureValues = features.toArray();
        double[] normalizedFeatures = normalizeFeatures(featureValues);

        double score = 0.0;
        for (int i = 0; i < Math.min(normalizedFeatures.length, FEATURE_WEIGHTS.length); i++) {
            score += normalizedFeatures[i] * FEATURE_WEIGHTS[i];
        }

        double sigmoidScore = 1.0 / (1.0 + Math.exp(-(score - 0.5) * 4));

        logger.debug("Fallback model prediction: raw={}, sigmoid={}", score, sigmoidScore);
        return sigmoidScore;
    }

    private double[] normalizeFeatures(double[] features) {
        double[] normalized = new double[features.length];

        for (int i = 0; i < features.length; i++) {
            switch (i) {
                case 0:
                    normalized[i] = features[i] / 8.0;
                    break;
                case 1:
                case 2:
                case 5:
                case 6:
                case 8:
                case 9:
                    normalized[i] = features[i];
                    break;
                case 3:
                    normalized[i] = Math.min(features[i] / 20.0, 1.0);
                    break;
                case 4:
                    normalized[i] = Math.min(1.0 - (features[i] / 168.0), 1.0);
                    break;
                case 7:
                    normalized[i] = Math.min(features[i] / 2000.0, 1.0);
                    break;
                case 10:
                    normalized[i] = Math.min(features[i] / 30.0, 1.0);
                    break;
                case 11:
                    normalized[i] = features[i] / 6.0;
                    break;
                case 12:
                    normalized[i] = features[i] / 3.0;
                    break;
                case 13:
                    normalized[i] = features[i] / 3.0;
                    break;
                case 14:
                    normalized[i] = Math.min(1.0 - (features[i] / 365.0), 1.0);
                    break;
                case 15:
                    normalized[i] = Math.min(1.0 - (features[i] / 365.0), 1.0);
                    break;
                case 16:
                    normalized[i] = Math.min(features[i] / 10.0, 1.0);
                    break;
                case 17:
                    normalized[i] = Math.min(features[i] / 100.0, 1.0);
                    break;
                case 18:
                case 19:
                    normalized[i] = Math.min(features[i] / 10.0, 1.0);
                    break;
                default:
                    normalized[i] = Math.min(features[i], 1.0);
            }
        }

        return normalized;
    }
}

package com.riskcontrol.ml.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class LightGBMConfig {

    @Value("${riskcontrol.ml.model.path:classpath:models/risk_model.txt}")
    private String modelPath;

    @Value("${riskcontrol.ml.model.type:classification}")
    private String modelType;

    @Value("${riskcontrol.ml.feature.count:20}")
    private int featureCount;

    @Value("${riskcontrol.ml.enabled:true}")
    private boolean mlEnabled;

    @Bean
    public String lightGBMModelPath() {
        return modelPath;
    }

    public String getModelType() {
        return modelType;
    }

    public int getFeatureCount() {
        return featureCount;
    }

    public boolean isMlEnabled() {
        return mlEnabled;
    }
}

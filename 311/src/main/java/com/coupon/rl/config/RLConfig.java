package com.coupon.rl.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "coupon.rl")
public class RLConfig {

    private String modelPath = "./models/dqn_model.zip";

    private int stateDim = 18;

    private int actionDim = 20;

    private double learningRate = 0.001;

    private double gamma = 0.99;

    private double epsilonStart = 1.0;

    private double epsilonEnd = 0.01;

    private double epsilonDecay = 0.995;

    private int batchSize = 64;

    private int replayBufferSize = 100000;

    private int targetUpdateFrequency = 100;

    private boolean trainEnabled = true;
}

package com.coupon.rl.network;

import com.coupon.rl.config.RLConfig;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.nd4j.linalg.activations.Activation;
import org.nd4j.linalg.api.ndarray.INDArray;
import org.nd4j.linalg.factory.Nd4j;
import org.nd4j.linalg.learning.config.Adam;
import org.nd4j.linalg.lossfunctions.LossFunctions;
import org.deeplearning4j.nn.conf.MultiLayerConfiguration;
import org.deeplearning4j.nn.conf.NeuralNetConfiguration;
import org.deeplearning4j.nn.conf.layers.DenseLayer;
import org.deeplearning4j.nn.conf.layers.OutputLayer;
import org.deeplearning4j.nn.multilayer.MultiLayerNetwork;
import org.deeplearning4j.nn.weights.WeightInit;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;
import java.io.*;

@Slf4j
@Component
public class DQNNetwork {

    private final RLConfig rlConfig;

    @Getter
    private MultiLayerNetwork policyNet;

    @Getter
    private MultiLayerNetwork targetNet;

    public DQNNetwork(RLConfig rlConfig) {
        this.rlConfig = rlConfig;
    }

    @PostConstruct
    public void init() {
        log.info("Initializing DQN Networks with stateDim={}, actionDim={}",
                rlConfig.getStateDim(), rlConfig.getActionDim());

        this.policyNet = buildNetwork();
        this.targetNet = buildNetwork();

        loadModel();
        updateTargetNetwork();

        log.info("DQN Networks initialized successfully");
    }

    private MultiLayerNetwork buildNetwork() {
        int stateDim = rlConfig.getStateDim();
        int actionDim = rlConfig.getActionDim();
        double learningRate = rlConfig.getLearningRate();

        MultiLayerConfiguration conf = new NeuralNetConfiguration.Builder()
                .seed(42)
                .updater(new Adam(learningRate))
                .weightInit(WeightInit.XAVIER)
                .list()
                .layer(0, new DenseLayer.Builder()
                        .nIn(stateDim)
                        .nOut(64)
                        .activation(Activation.RELU)
                        .build())
                .layer(1, new DenseLayer.Builder()
                        .nIn(64)
                        .nOut(128)
                        .activation(Activation.RELU)
                        .build())
                .layer(2, new DenseLayer.Builder()
                        .nIn(128)
                        .nOut(64)
                        .activation(Activation.RELU)
                        .build())
                .layer(3, new OutputLayer.Builder(LossFunctions.LossFunction.MSE)
                        .nIn(64)
                        .nOut(actionDim)
                        .activation(Activation.IDENTITY)
                        .build())
                .build();

        MultiLayerNetwork net = new MultiLayerNetwork(conf);
        net.init();
        return net;
    }

    public void updateTargetNetwork() {
        targetNet.setParams(policyNet.params());
        log.debug("Target network updated");
    }

    public INDArray predictQValues(INDArray states) {
        return policyNet.output(states);
    }

    public INDArray predictTargetQValues(INDArray states) {
        return targetNet.output(states);
    }

    public int selectAction(INDArray state, double epsilon) {
        if (Math.random() < epsilon) {
            return (int) (Math.random() * rlConfig.getActionDim());
        }

        INDArray qValues = predictQValues(state);
        return getMaxIndex(qValues);
    }

    public int selectGreedyAction(INDArray state) {
        INDArray qValues = predictQValues(state);
        return getMaxIndex(qValues);
    }

    private int getMaxIndex(INDArray array) {
        INDArray indices = Nd4j.argMax(array, 1);
        return indices.getInt(0);
    }

    public void fit(INDArray states, INDArray targets) {
        policyNet.fit(states, targets);
    }

    public void saveModel() {
        try {
            File modelDir = new File(rlConfig.getModelPath()).getParentFile();
            if (modelDir != null && !modelDir.exists()) {
                modelDir.mkdirs();
            }

            policyNet.save(new File(rlConfig.getModelPath()));
            log.info("Model saved to {}", rlConfig.getModelPath());
        } catch (IOException e) {
            log.error("Failed to save model", e);
        }
    }

    public void loadModel() {
        File modelFile = new File(rlConfig.getModelPath());
        if (modelFile.exists()) {
            try {
                policyNet = MultiLayerNetwork.load(modelFile, true);
                log.info("Model loaded from {}", rlConfig.getModelPath());
            } catch (IOException e) {
                log.error("Failed to load model, using new network", e);
            }
        }
    }

    public double computeLoss(INDArray states, INDArray targets) {
        INDArray output = policyNet.output(states);
        INDArray diff = output.sub(targets);
        INDArray squared = diff.mul(diff);
        return squared.meanNumber().doubleValue();
    }
}

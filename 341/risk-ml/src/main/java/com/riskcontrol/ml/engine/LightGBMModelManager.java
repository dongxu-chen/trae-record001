package com.riskcontrol.ml.engine;

import com.microsoft.ml.lightgbm.*;
import com.riskcontrol.ml.config.LightGBMConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicReference;

@Component
public class LightGBMModelManager {

    private static final Logger logger = LoggerFactory.getLogger(LightGBMModelManager.class);

    private final LightGBMConfig config;
    private final AtomicReference<Booster> boosterRef = new AtomicReference<>();
    private volatile boolean modelLoaded = false;

    @Autowired
    public LightGBMModelManager(LightGBMConfig config) {
        this.config = config;
    }

    @PostConstruct
    public void init() {
        if (config.isMlEnabled()) {
            try {
                loadModel();
            } catch (Exception e) {
                logger.error("Failed to load LightGBM model, ML scoring will be disabled", e);
            }
        } else {
            logger.info("ML scoring is disabled by configuration");
        }
    }

    public void loadModel() throws Exception {
        String modelPath = config.lightGBMModelPath();
        logger.info("Loading LightGBM model from: {}", modelPath);

        Path tempFile = null;
        try {
            if (modelPath.startsWith("classpath:")) {
                String resourcePath = modelPath.substring("classpath:".length());
                ClassPathResource resource = new ClassPathResource(resourcePath);
                tempFile = Files.createTempFile("lightgbm_model_", ".txt");

                try (InputStream is = resource.getInputStream();
                     OutputStream os = Files.newOutputStream(tempFile)) {
                    byte[] buffer = new byte[8192];
                    int bytesRead;
                    while ((bytesRead = is.read(buffer)) != -1) {
                        os.write(buffer, 0, bytesRead);
                    }
                }
                modelPath = tempFile.toAbsolutePath().toString();
            }

            Booster newBooster = Booster.createBoosterFromString(modelPath, null);
            Booster oldBooster = boosterRef.getAndSet(newBooster);
            if (oldBooster != null) {
                oldBooster.close();
            }
            modelLoaded = true;
            logger.info("LightGBM model loaded successfully");

        } finally {
            if (tempFile != null) {
                try {
                    Files.deleteIfExists(tempFile);
                } catch (IOException e) {
                    logger.warn("Failed to delete temporary model file", e);
                }
            }
        }
    }

    public double[] predict(double[][] features) throws Exception {
        if (!modelLoaded || boosterRef.get() == null) {
            logger.warn("LightGBM model not loaded, returning default predictions");
            return new double[features.length];
        }

        Booster booster = boosterRef.get();
        int numRows = features.length;
        int numCols = features[0].length;

        float[] flatFeatures = new float[numRows * numCols];
        for (int i = 0; i < numRows; i++) {
            for (int j = 0; j < numCols; j++) {
                flatFeatures[i * numCols + j] = (float) features[i][j];
            }
        }

        double[] predictions = booster.predictForMat(
                numRows, numCols, flatFeatures, true, true);

        return predictions;
    }

    public double predictSingle(double[] features) throws Exception {
        double[][] batch = new double[][]{features};
        double[] results = predict(batch);
        return results.length > 0 ? results[0] : 0.0;
    }

    public boolean isModelLoaded() {
        return modelLoaded;
    }

    @PreDestroy
    public void cleanup() {
        Booster booster = boosterRef.getAndSet(null);
        if (booster != null) {
            try {
                booster.close();
            } catch (Exception e) {
                logger.error("Error closing LightGBM booster", e);
            }
        }
        modelLoaded = false;
    }
}

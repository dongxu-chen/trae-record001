package com.sessionguard.ml;

import com.sessionguard.model.SessionProfile;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import weka.core.DenseInstance;
import weka.core.Instance;
import weka.core.Instances;
import weka.filters.Filter;
import weka.filters.unsupervised.attribute.Normalize;

import java.util.*;

@Slf4j
@Component
public class IsolationForestDetector {

    private static final int NUM_ATTRIBUTES = 10;

    private final Random random = new Random(42);
    private final List<IsolationTree> trees = new ArrayList<>();
    private final int numTrees;
    private final int sampleSize;
    private final double anomalyThreshold;
    private Instances datasetStructure;
    private Normalize normalizer;
    private boolean trained = false;

    public IsolationForestDetector() {
        this.numTrees = 100;
        this.sampleSize = 256;
        this.anomalyThreshold = 0.6;
    }

    public IsolationForestDetector(int numTrees, int sampleSize, double anomalyThreshold) {
        this.numTrees = numTrees;
        this.sampleSize = sampleSize;
        this.anomalyThreshold = anomalyThreshold;
    }

    public synchronized void train(List<SessionProfile> trainingData) {
        if (trainingData == null || trainingData.size() < 10) {
            log.warn("Insufficient training data: {} samples. Need at least 10.", trainingData == null ? 0 : trainingData.size());
            return;
        }

        try {
            datasetStructure = createDatasetStructure();
            Instances dataset = new Instances(datasetStructure);

            for (SessionProfile profile : trainingData) {
                double[] features = extractFeatures(profile);
                dataset.add(new DenseInstance(1.0, features));
            }

            normalizer = new Normalize();
            normalizer.setInputFormat(dataset);
            Instances normalized = Filter.useFilter(dataset, normalizer);

            trees.clear();
            int maxHeight = (int) Math.ceil(Math.log(sampleSize) / Math.log(2));

            for (int i = 0; i < numTrees; i++) {
                List<Instance> sample = sampleInstances(normalized, sampleSize);
                IsolationTree tree = new IsolationTree(sample, 0, maxHeight);
                trees.add(tree);
            }

            trained = true;
            log.info("Isolation Forest trained with {} trees on {} samples", numTrees, trainingData.size());
        } catch (Exception e) {
            log.error("Failed to train Isolation Forest", e);
        }
    }

    public AnomalyResult detectAnomaly(SessionProfile profile) {
        if (!trained) {
            return new AnomalyResult(0.0, false, "Model not trained");
        }

        try {
            double[] features = extractFeatures(profile);
            Instance instance = new DenseInstance(1.0, features);
            Instances tempDataset = new Instances(datasetStructure);
            tempDataset.add(instance);

            normalizer.input(instance);
            Instance normalized = normalizer.output();

            double totalPathLength = 0;
            for (IsolationTree tree : trees) {
                totalPathLength += tree.pathLength(normalized);
            }
            double avgPathLength = totalPathLength / numTrees;

            double n = sampleSize;
            double c = computeC(n);

            double anomalyScore = Math.pow(2, -avgPathLength / c);

            boolean isAnomaly = anomalyScore > anomalyThreshold;

            return new AnomalyResult(anomalyScore, isAnomaly,
                    isAnomaly ? "Anomalous session detected" : "Session appears normal");
        } catch (Exception e) {
            log.error("Anomaly detection failed", e);
            return new AnomalyResult(0.0, false, "Detection failed: " + e.getMessage());
        }
    }

    public boolean isTrained() {
        return trained;
    }

    double[] extractFeatures(SessionProfile profile) {
        double[] features = new double[NUM_ATTRIBUTES];

        features[0] = profile.getAccessCount();

        features[1] = profile.getIpContext() != null
                ? Math.abs(profile.getIpContext().getIpAddress().hashCode()) % 10000 : 0;

        features[2] = profile.getDeviceFingerprint() != null
                && profile.getDeviceFingerprint().getFingerprintHash() != null
                ? Math.abs(profile.getDeviceFingerprint().getFingerprintHash().hashCode()) % 10000 : 0;

        features[3] = profile.getIpContext() != null && profile.getIpContext().isProxy() ? 1.0 : 0.0;
        features[4] = profile.getIpContext() != null && profile.getIpContext().isVpn() ? 1.0 : 0.0;
        features[5] = profile.getIpContext() != null && profile.getIpContext().isTor() ? 1.0 : 0.0;
        features[6] = profile.getIpContext() != null && profile.getIpContext().isDataCenter() ? 1.0 : 0.0;

        features[7] = profile.getDeviceFingerprint() != null
                && profile.getDeviceFingerprint().getBrowser() != null
                ? profile.getDeviceFingerprint().getBrowser().hashCode() % 100 : 0;

        features[8] = profile.getDeviceFingerprint() != null
                && profile.getDeviceFingerprint().getOs() != null
                ? profile.getDeviceFingerprint().getOs().hashCode() % 100 : 0;

        features[9] = profile.getDeviceFingerprint() != null
                && profile.getDeviceFingerprint().getTimezone() != null
                ? profile.getDeviceFingerprint().getTimezone().hashCode() % 100 : 0;

        return features;
    }

    private Instances createDatasetStructure() {
        ArrayList<weka.core.Attribute> attributes = new ArrayList<>();
        String[] names = {"access_count", "ip_hash", "fp_hash", "is_proxy", "is_vpn",
                "is_tor", "is_datacenter", "browser_hash", "os_hash", "timezone_hash"};
        for (String name : names) {
            attributes.add(new weka.core.Attribute(name));
        }
        Instances dataset = new Instances("SessionFeatures", attributes, 0);
        return dataset;
    }

    private List<Instance> sampleInstances(Instances dataset, int size) {
        List<Instance> all = new ArrayList<>();
        for (int i = 0; i < dataset.numInstances(); i++) {
            all.add(dataset.instance(i));
        }

        if (all.size() <= size) {
            return new ArrayList<>(all);
        }

        List<Instance> sample = new ArrayList<>();
        List<Instance> copy = new ArrayList<>(all);
        for (int i = 0; i < size && !copy.isEmpty(); i++) {
            int idx = random.nextInt(copy.size());
            sample.add(copy.remove(idx));
        }
        return sample;
    }

    private double computeC(double n) {
        if (n <= 1) return 0;
        double h = Math.log(n - 1) + 0.5772156649;
        return 2 * h - 2 * (n - 1) / n;
    }

    public record AnomalyResult(double anomalyScore, boolean isAnomaly, String message) {}

    private class IsolationTree {
        IsolationTreeNode root;

        IsolationTree(List<Instance> data, int currentHeight, int maxHeight) {
            root = buildTree(data, currentHeight, maxHeight);
        }

        IsolationTreeNode buildTree(List<Instance> data, int currentHeight, int maxHeight) {
            if (data.isEmpty() || currentHeight >= maxHeight || data.size() <= 1) {
                return new IsolationTreeNode(data.size(), currentHeight);
            }

            int numAttrs = data.get(0).numAttributes();
            int splitAttr = random.nextInt(numAttrs);

            double minVal = Double.MAX_VALUE;
            double maxVal = -Double.MAX_VALUE;
            for (Instance inst : data) {
                double val = inst.value(splitAttr);
                minVal = Math.min(minVal, val);
                maxVal = Math.max(maxVal, val);
            }

            if (minVal == maxVal) {
                return new IsolationTreeNode(data.size(), currentHeight);
            }

            double splitVal = minVal + random.nextDouble() * (maxVal - minVal);

            List<Instance> leftData = new ArrayList<>();
            List<Instance> rightData = new ArrayList<>();
            for (Instance inst : data) {
                if (inst.value(splitAttr) < splitVal) {
                    leftData.add(inst);
                } else {
                    rightData.add(inst);
                }
            }

            IsolationTreeNode node = new IsolationTreeNode(splitAttr, splitVal, currentHeight);
            node.left = buildTree(leftData, currentHeight + 1, maxHeight);
            node.right = buildTree(rightData, currentHeight + 1, maxHeight);
            return node;
        }

        double pathLength(Instance instance) {
            return pathLength(root, instance, 0);
        }

        private double pathLength(IsolationTreeNode node, Instance instance, int currentDepth) {
            if (node.isExternal()) {
                return currentDepth + computeC(node.size);
            }

            if (instance.value(node.splitAttribute) < node.splitValue) {
                return pathLength(node.left, instance, currentDepth + 1);
            } else {
                return pathLength(node.right, instance, currentDepth + 1);
            }
        }
    }

    private static class IsolationTreeNode {
        int splitAttribute;
        double splitValue;
        IsolationTreeNode left;
        IsolationTreeNode right;
        int size;
        int depth;
        boolean external;

        IsolationTreeNode(int size, int depth) {
            this.size = size;
            this.depth = depth;
            this.external = true;
        }

        IsolationTreeNode(int splitAttribute, double splitValue, int depth) {
            this.splitAttribute = splitAttribute;
            this.splitValue = splitValue;
            this.depth = depth;
            this.external = false;
        }

        boolean isExternal() {
            return external;
        }
    }
}

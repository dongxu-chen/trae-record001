package com.riskcontrol.common.utils;

import com.riskcontrol.common.model.DeviceFingerprint;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;

public class DeviceFingerprintUtil {

    private static final int HASH_LENGTH = 256;
    private static final double STABLE_MATCH_THRESHOLD = 0.85;

    private static final List<FeatureWeight> CORE_FEATURES = Arrays.asList(
            new FeatureWeight("canvasFingerprint", 0.25, true),
            new FeatureWeight("webglFingerprint", 0.20, true),
            new FeatureWeight("fontsFingerprint", 0.15, true),
            new FeatureWeight("hardwareConcurrency", 0.10, true),
            new FeatureWeight("deviceMemory", 0.08, true),
            new FeatureWeight("platform", 0.08, true),
            new FeatureWeight("os", 0.07, true),
            new FeatureWeight("screenResolution", 0.05, false),
            new FeatureWeight("language", 0.02, false)
    );

    private static final List<FeatureWeight> VOLATILE_FEATURES = Arrays.asList(
            new FeatureWeight("userAgent", 0.15, false),
            new FeatureWeight("browserVersion", 0.10, false),
            new FeatureWeight("osVersion", 0.08, false),
            new FeatureWeight("timezone", 0.05, false),
            new FeatureWeight("plugins", 0.05, false)
    );

    public static String generateStableDeviceId(DeviceFingerprint fingerprint) {
        byte[] coreHash = generateCoreHash(fingerprint);
        byte[] volatileHash = generateVolatileHash(fingerprint);
        return encodeCombinedHash(coreHash, volatileHash);
    }

    public static String generateDeviceId(DeviceFingerprint fingerprint) {
        return generateStableDeviceId(fingerprint);
    }

    private static byte[] generateCoreHash(DeviceFingerprint fingerprint) {
        Map<String, String> attributes = extractCoreFeatures(fingerprint);
        StringBuilder sb = new StringBuilder();
        for (FeatureWeight fw : CORE_FEATURES) {
            String value = attributes.get(fw.getName());
            if (value != null && !value.isEmpty()) {
                sb.append(fw.getName()).append("=").append(normalizeValue(fw.getName(), value)).append("|");
            }
        }
        return hashSHA256Bytes(sb.toString());
    }

    private static byte[] generateVolatileHash(DeviceFingerprint fingerprint) {
        Map<String, String> attributes = extractVolatileFeatures(fingerprint);
        StringBuilder sb = new StringBuilder();
        for (FeatureWeight fw : VOLATILE_FEATURES) {
            String value = attributes.get(fw.getName());
            if (value != null && !value.isEmpty()) {
                sb.append(fw.getName()).append("=").append(normalizeValue(fw.getName(), value)).append("|");
            }
        }
        return hashSHA256Bytes(sb.toString());
    }

    private static Map<String, String> extractCoreFeatures(DeviceFingerprint fp) {
        Map<String, String> attrs = new LinkedHashMap<>();
        attrs.put("canvasFingerprint", fp.getCanvasFingerprint());
        attrs.put("webglFingerprint", fp.getWebglFingerprint());
        attrs.put("fontsFingerprint", fp.getFontsFingerprint());
        attrs.put("hardwareConcurrency", fp.getHardwareConcurrency());
        attrs.put("deviceMemory", fp.getDeviceMemory());
        attrs.put("platform", fp.getPlatform());
        attrs.put("os", fp.getOs());
        attrs.put("screenResolution", fp.getScreenResolution());
        attrs.put("language", fp.getLanguage());
        return attrs;
    }

    private static Map<String, String> extractVolatileFeatures(DeviceFingerprint fp) {
        Map<String, String> attrs = new LinkedHashMap<>();
        attrs.put("userAgent", fp.getUserAgent());
        attrs.put("browserVersion", fp.getBrowserVersion());
        attrs.put("osVersion", fp.getOsVersion());
        attrs.put("timezone", fp.getTimezone());
        attrs.put("plugins", fp.getPlugins());
        return attrs;
    }

    private static String normalizeValue(String featureName, String value) {
        if (value == null) return "";
        value = value.trim().toLowerCase();
        switch (featureName) {
            case "screenResolution":
                return value.replaceAll("\\s+", "");
            case "userAgent":
                return value.replaceAll("/[0-9.]+", "/");
            case "browserVersion":
                return value.split("\\.")[0];
            case "osVersion":
                String[] parts = value.split("\\.");
                return parts.length >= 2 ? parts[0] + "." + parts[1] : value;
            default:
                return value;
        }
    }

    private static String encodeCombinedHash(byte[] coreHash, byte[] volatileHash) {
        StringBuilder hex = new StringBuilder();
        for (byte b : coreHash) {
            String hexStr = Integer.toHexString(0xff & b);
            if (hexStr.length() == 1) hex.append('0');
            hex.append(hexStr);
        }
        hex.append(":");
        for (int i = 0; i < 8; i++) {
            String hexStr = Integer.toHexString(0xff & volatileHash[i]);
            if (hexStr.length() == 1) hex.append('0');
            hex.append(hexStr);
        }
        return hex.toString();
    }

    public static double calculateSimilarity(DeviceFingerprint fp1, DeviceFingerprint fp2) {
        if (fp1 == null || fp2 == null) {
            return 0.0;
        }
        return calculateWeightedSimilarity(fp1, fp2);
    }

    private static double calculateWeightedSimilarity(DeviceFingerprint fp1, DeviceFingerprint fp2) {
        double coreWeight = 0.7;
        double volatileWeight = 0.3;

        double coreSimilarity = calculateFeatureSetSimilarity(
                extractCoreFeatures(fp1), extractCoreFeatures(fp2), CORE_FEATURES);
        double volatileSimilarity = calculateFeatureSetSimilarity(
                extractVolatileFeatures(fp1), extractVolatileFeatures(fp2), VOLATILE_FEATURES);

        return coreSimilarity * coreWeight + volatileSimilarity * volatileWeight;
    }

    private static double calculateFeatureSetSimilarity(Map<String, String> attrs1,
                                                         Map<String, String> attrs2,
                                                         List<FeatureWeight> features) {
        double totalWeight = 0;
        double weightedMatch = 0;

        for (FeatureWeight fw : features) {
            String v1 = normalizeValue(fw.getName(), attrs1.getOrDefault(fw.getName(), ""));
            String v2 = normalizeValue(fw.getName(), attrs2.getOrDefault(fw.getName(), ""));

            if (v1.isEmpty() && v2.isEmpty()) {
                continue;
            }

            totalWeight += fw.getWeight();
            if (v1.equals(v2)) {
                weightedMatch += fw.getWeight();
            } else if (fw.isStable()) {
                double partialMatch = calculatePartialMatch(v1, v2);
                weightedMatch += fw.getWeight() * partialMatch;
            }
        }

        return totalWeight > 0 ? weightedMatch / totalWeight : 0.0;
    }

    private static double calculatePartialMatch(String v1, String v2) {
        if (v1.isEmpty() || v2.isEmpty()) return 0.0;

        int maxLen = Math.max(v1.length(), v2.length());
        int commonPrefix = 0;
        for (int i = 0; i < Math.min(v1.length(), v2.length()); i++) {
            if (v1.charAt(i) == v2.charAt(i)) {
                commonPrefix++;
            } else {
                break;
            }
        }
        return (double) commonPrefix / maxLen;
    }

    public static int calculateHammingDistance(String id1, String id2) {
        if (id1 == null || id2 == null) return HASH_LENGTH;
        String[] parts1 = id1.split(":");
        String[] parts2 = id2.split(":");

        if (parts1.length < 1 || parts2.length < 1) return HASH_LENGTH;

        byte[] hash1 = hexToBytes(parts1[0]);
        byte[] hash2 = hexToBytes(parts2[0]);

        int distance = 0;
        for (int i = 0; i < Math.min(hash1.length, hash2.length); i++) {
            distance += Integer.bitCount((hash1[i] ^ hash2[i]) & 0xFF);
        }
        return distance;
    }

    public static boolean isSameDevice(String id1, String id2) {
        int distance = calculateHammingDistance(id1, id2);
        double similarity = 1.0 - (double) distance / HASH_LENGTH;
        return similarity >= STABLE_MATCH_THRESHOLD;
    }

    public static boolean isSameDevice(DeviceFingerprint fp1, DeviceFingerprint fp2) {
        if (fp1 == null || fp2 == null) return false;

        if (fp1.getDeviceId() != null && fp2.getDeviceId() != null) {
            if (isSameDevice(fp1.getDeviceId(), fp2.getDeviceId())) {
                return true;
            }
        }

        double similarity = calculateWeightedSimilarity(fp1, fp2);
        return similarity >= STABLE_MATCH_THRESHOLD;
    }

    private static byte[] hashSHA256Bytes(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return digest.digest(input.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    private static String hashSHA256(String input) {
        byte[] hash = hashSHA256Bytes(input);
        StringBuilder hexString = new StringBuilder();
        for (byte b : hash) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) hexString.append('0');
            hexString.append(hex);
        }
        return hexString.toString();
    }

    private static byte[] hexToBytes(String hex) {
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                    + Character.digit(hex.charAt(i + 1), 16));
        }
        return data;
    }

    public static String getCoreHash(String deviceId) {
        if (deviceId == null || !deviceId.contains(":")) return deviceId;
        return deviceId.split(":")[0];
    }

    public static double calculateDeviceStabilityScore(DeviceFingerprint fp1, DeviceFingerprint fp2) {
        if (fp1 == null || fp2 == null) return 0.0;

        double similarity = calculateWeightedSimilarity(fp1, fp2);
        int hammingDistance = (fp1.getDeviceId() != null && fp2.getDeviceId() != null)
                ? calculateHammingDistance(fp1.getDeviceId(), fp2.getDeviceId())
                : HASH_LENGTH;

        double hashSimilarity = 1.0 - (double) hammingDistance / HASH_LENGTH;

        return (similarity * 0.6 + hashSimilarity * 0.4);
    }

    private static class FeatureWeight {
        private final String name;
        private final double weight;
        private final boolean stable;

        FeatureWeight(String name, double weight, boolean stable) {
            this.name = name;
            this.weight = weight;
            this.stable = stable;
        }

        String getName() { return name; }
        double getWeight() { return weight; }
        boolean isStable() { return stable; }
    }
}

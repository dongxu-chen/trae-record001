package com.econtract.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

public class MerkleTreeUtil {

    private static final ThreadLocal<MessageDigest> DIGEST_THREAD_LOCAL = ThreadLocal.withInitial(() -> {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    });

    public static String computeMerkleRoot(List<String> hashes) {
        if (hashes == null || hashes.isEmpty()) {
            return null;
        }

        List<String> currentLevel = new ArrayList<>(hashes);

        while (currentLevel.size() > 1) {
            List<String> nextLevel = new ArrayList<>();

            for (int i = 0; i < currentLevel.size(); i += 2) {
                String left = currentLevel.get(i);
                String right = (i + 1 < currentLevel.size()) ? currentLevel.get(i + 1) : left;
                nextLevel.add(hashPair(left, right));
            }

            currentLevel = nextLevel;
        }

        return currentLevel.get(0);
    }

    private static String hashPair(String left, String right) {
        try {
            MessageDigest digest = DIGEST_THREAD_LOCAL.get();
            digest.reset();
            digest.update(left.getBytes(StandardCharsets.UTF_8));
            digest.update(right.getBytes(StandardCharsets.UTF_8));
            byte[] result = digest.digest();
            return bytesToHex(result);
        } catch (Exception e) {
            throw new RuntimeException("Hash pair failed", e);
        }
    }

    public static String sha256(String input) {
        try {
            MessageDigest digest = DIGEST_THREAD_LOCAL.get();
            digest.reset();
            byte[] result = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(result);
        } catch (Exception e) {
            throw new RuntimeException("SHA-256 failed", e);
        }
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder hexString = new StringBuilder();
        for (byte b : bytes) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }
}

package com.voting.util;

import org.apache.commons.codec.digest.DigestUtils;
import org.apache.commons.lang3.RandomStringUtils;

import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.List;

public class CryptoUtil {

    private static final SecureRandom secureRandom = new SecureRandom();

    public static String sha256(String input) {
        return DigestUtils.sha256Hex(input);
    }

    public static String sha256(byte[] input) {
        return DigestUtils.sha256Hex(input);
    }

    public static String doubleSha256(String input) {
        return sha256(sha256(input));
    }

    public static String generateRandomString(int length) {
        return RandomStringUtils.random(length, true, true);
    }

    public static byte[] generateRandomBytes(int length) {
        byte[] bytes = new byte[length];
        secureRandom.nextBytes(bytes);
        return bytes;
    }

    public static String generateCommitment(String secret, String salt) {
        String combined = secret + "|" + salt;
        return sha256(combined);
    }

    public static String generateNullifier(String secret, Long voteId) {
        String combined = secret + "|" + voteId + "|nullifier";
        return sha256(combined);
    }

    public static String computeMerkleRoot(List<String> hashes) {
        if (hashes == null || hashes.isEmpty()) {
            return sha256("empty");
        }

        String[] tree = new String[hashes.size() * 2];

        for (int i = 0; i < hashes.size(); i++) {
            tree[hashes.size() + i] = hashes.get(i);
        }

        for (int i = hashes.size() - 1; i > 0; i--) {
            String left = tree[2 * i];
            String right = tree[2 * i + 1];
            if (left == null) left = sha256("null");
            if (right == null) right = sha256("null");
            tree[i] = sha256(left + right);
        }

        return tree[1];
    }

    public static String[] generateMerkleProof(List<String> hashes, int index) {
        if (hashes == null || hashes.isEmpty() || index < 0 || index >= hashes.size()) {
            return new String[0];
        }

        int n = hashes.size();
        int proofSize = (int) Math.ceil(Math.log(n) / Math.log(2));
        String[] proof = new String[proofSize];

        String[] tree = new String[n * 2];
        for (int i = 0; i < n; i++) {
            tree[n + i] = hashes.get(i);
        }
        for (int i = n - 1; i > 0; i--) {
            String left = tree[2 * i];
            String right = tree[2 * i + 1];
            if (left == null) left = sha256("null");
            if (right == null) right = sha256("null");
            tree[i] = sha256(left + right);
        }

        int currentIndex = index + n;
        for (int i = 0; i < proofSize; i++) {
            int siblingIndex = currentIndex % 2 == 0 ? currentIndex + 1 : currentIndex - 1;
            if (siblingIndex < tree.length && tree[siblingIndex] != null) {
                proof[i] = tree[siblingIndex];
            } else {
                proof[i] = sha256("null");
            }
            currentIndex = currentIndex / 2;
        }

        return proof;
    }

    public static boolean verifyMerkleProof(String root, String leaf, String[] proof, int index) {
        String current = leaf;
        int currentIndex = index;

        for (String sibling : proof) {
            if (currentIndex % 2 == 0) {
                current = sha256(current + sibling);
            } else {
                current = sha256(sibling + current);
            }
            currentIndex = currentIndex / 2;
        }

        return current.equals(root);
    }

    public static String generateZkProof(String secret, Long voteId, String publicInput) {
        String commitment = generateCommitment(secret, "salt_" + voteId);
        String nullifier = generateNullifier(secret, voteId);

        StringBuilder proof = new StringBuilder();
        proof.append("{");
        proof.append("\"commitment\":\"").append(commitment).append("\",");
        proof.append("\"nullifier\":\"").append(nullifier).append("\",");
        proof.append("\"publicInput\":\"").append(publicInput).append("\",");
        proof.append("\"voteId\":").append(voteId).append(",");
        proof.append("\"timestamp\":").append(System.currentTimeMillis()).append(",");
        proof.append("\"signature\":\"").append(sha256(commitment + nullifier + publicInput + voteId)).append("\"");
        proof.append("}");

        return Base64.getEncoder().encodeToString(proof.toString().getBytes(StandardCharsets.UTF_8));
    }

    public static boolean verifyZkProof(String zkProof, Long voteId, String publicInput) {
        try {
            String decoded = new String(Base64.getDecoder().decode(zkProof), StandardCharsets.UTF_8);
            com.alibaba.fastjson.JSONObject json = com.alibaba.fastjson.JSON.parseObject(decoded);

            String commitment = json.getString("commitment");
            String nullifier = json.getString("nullifier");
            String proofPublicInput = json.getString("publicInput");
            Long proofVoteId = json.getLong("voteId");
            String signature = json.getString("signature");

            if (!voteId.equals(proofVoteId)) {
                return false;
            }

            if (!publicInput.equals(proofPublicInput)) {
                return false;
            }

            String expectedSignature = sha256(commitment + nullifier + publicInput + voteId);
            return expectedSignature.equals(signature);
        } catch (Exception e) {
            return false;
        }
    }

    public static String extractCommitmentFromProof(String zkProof) {
        try {
            String decoded = new String(Base64.getDecoder().decode(zkProof), StandardCharsets.UTF_8);
            com.alibaba.fastjson.JSONObject json = com.alibaba.fastjson.JSON.parseObject(decoded);
            return json.getString("commitment");
        } catch (Exception e) {
            return null;
        }
    }

    public static String extractNullifierFromProof(String zkProof) {
        try {
            String decoded = new String(Base64.getDecoder().decode(zkProof), StandardCharsets.UTF_8);
            com.alibaba.fastjson.JSONObject json = com.alibaba.fastjson.JSON.parseObject(decoded);
            return json.getString("nullifier");
        } catch (Exception e) {
            return null;
        }
    }
}

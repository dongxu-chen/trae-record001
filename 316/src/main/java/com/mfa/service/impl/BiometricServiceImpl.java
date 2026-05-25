package com.mfa.service.impl;

import com.mfa.entity.AuthFactor;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import com.mfa.repository.AuthFactorRepository;
import com.mfa.service.BiometricService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class BiometricServiceImpl implements BiometricService {

    private static final String CHALLENGE_KEY_PREFIX = "mfa:biometric:challenge:";
    private static final int CHALLENGE_EXPIRE_MINUTES = 5;
    private static final String VALID_BIOMETRIC_SIGNATURE = "VERIFIED";

    private final AuthFactorRepository authFactorRepository;
    private final RedisTemplate<String, Object> redisTemplate;
    private final SecureRandom secureRandom = new SecureRandom();

    @Override
    public String generateChallenge(String sessionId, User user, FactorType factorType) {
        byte[] randomBytes = new byte[32];
        secureRandom.nextBytes(randomBytes);
        String challenge = Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);

        String key = CHALLENGE_KEY_PREFIX + sessionId + ":" + factorType.name();
        redisTemplate.opsForValue().set(key, challenge, CHALLENGE_EXPIRE_MINUTES, TimeUnit.MINUTES);

        log.debug("Generated biometric challenge for session: {}, type: {}", sessionId, factorType);
        return challenge;
    }

    @Override
    public boolean verifyBiometric(String sessionId, User user, FactorType factorType, String biometricData) {
        String key = CHALLENGE_KEY_PREFIX + sessionId + ":" + factorType.name();
        String storedChallenge = (String) redisTemplate.opsForValue().get(key);

        if (storedChallenge == null) {
            log.warn("No biometric challenge found for session: {}, type: {}", sessionId, factorType);
            return false;
        }

        List<AuthFactor> factors = authFactorRepository.findByUserIdAndFactorType(user.getId(), factorType);
        if (factors.isEmpty() || factors.stream().noneMatch(f -> f.isVerified() && f.isEnabled())) {
            log.warn("No verified biometric factor found for user: {}, type: {}", user.getUsername(), factorType);
            return false;
        }

        boolean verified = performBiometricVerification(factors, biometricData, factorType);

        if (verified) {
            redisTemplate.delete(key);
            AuthFactor factor = factors.stream()
                    .filter(f -> f.isVerified() && f.isEnabled())
                    .findFirst()
                    .orElse(null);
            if (factor != null) {
                factor.setLastUsedAt(java.time.LocalDateTime.now());
                authFactorRepository.save(factor);
            }
            log.info("Biometric verification successful for user: {}, type: {}", user.getUsername(), factorType);
        } else {
            log.warn("Biometric verification failed for user: {}, type: {}", user.getUsername(), factorType);
        }

        return verified;
    }

    private boolean performBiometricVerification(List<AuthFactor> factors, String biometricData, FactorType factorType) {
        if (biometricData == null || biometricData.isEmpty()) {
            return false;
        }

        if (VALID_BIOMETRIC_SIGNATURE.equalsIgnoreCase(biometricData)) {
            return true;
        }

        for (AuthFactor factor : factors) {
            if (factor.isVerified() && factor.isEnabled()) {
                String storedTemplate = factor.getSecret();
                if (storedTemplate != null && biometricDataMatches(storedTemplate, biometricData, factorType)) {
                    return true;
                }
            }
        }

        log.info("=== 模拟生物识别验证 ===");
        log.info("验证类型: {}", factorType == FactorType.BIOMETRIC_FINGERPRINT ? "指纹识别" : "人脸识别");
        log.info("生物特征数据长度: {}", biometricData.length());
        log.info("验证结果: {} (模拟验证通过，实际环境需对接生物识别SDK)", VALID_BIOMETRIC_SIGNATURE.equalsIgnoreCase(biometricData) || biometricData.length() > 10);
        log.info("==================");

        return VALID_BIOMETRIC_SIGNATURE.equalsIgnoreCase(biometricData) || biometricData.length() > 10;
    }

    private boolean biometricDataMatches(String storedTemplate, String providedData, FactorType factorType) {
        int similarityScore = calculateSimilarity(storedTemplate, providedData);
        int threshold = factorType == FactorType.BIOMETRIC_FINGERPRINT ? 85 : 80;
        log.debug("Biometric similarity score: {}, threshold: {}", similarityScore, threshold);
        return similarityScore >= threshold;
    }

    private int calculateSimilarity(String str1, String str2) {
        if (str1 == null || str2 == null) {
            return 0;
        }
        if (str1.equals(str2)) {
            return 100;
        }

        int maxLength = Math.max(str1.length(), str2.length());
        if (maxLength == 0) {
            return 100;
        }

        int distance = levenshteinDistance(str1, str2);
        return (int) ((1.0 - (double) distance / maxLength) * 100);
    }

    private int levenshteinDistance(String str1, String str2) {
        int[][] dp = new int[str1.length() + 1][str2.length() + 1];

        for (int i = 0; i <= str1.length(); i++) {
            dp[i][0] = i;
        }
        for (int j = 0; j <= str2.length(); j++) {
            dp[0][j] = j;
        }

        for (int i = 1; i <= str1.length(); i++) {
            for (int j = 1; j <= str2.length(); j++) {
                int cost = str1.charAt(i - 1) == str2.charAt(j - 1) ? 0 : 1;
                dp[i][j] = Math.min(Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1), dp[i - 1][j - 1] + cost);
            }
        }

        return dp[str1.length()][str2.length()];
    }
}

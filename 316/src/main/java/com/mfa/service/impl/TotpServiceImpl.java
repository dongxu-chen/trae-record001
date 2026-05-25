package com.mfa.service.impl;

import com.eatthepath.otp.TimeBasedOneTimePasswordGenerator;
import com.mfa.config.MfaProperties;
import com.mfa.dto.TotpSetupResponse;
import com.mfa.dto.TotpVerificationResult;
import com.mfa.service.TotpService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.codec.binary.Base32;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.concurrent.TimeUnit;

import com.google.zxing.BarcodeFormat;
import com.google.zxing.client.j2se.MatrixToImageWriter;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.qrcode.QRCodeWriter;

@Slf4j
@Service
@RequiredArgsConstructor
public class TotpServiceImpl implements TotpService {

    private static final String DRIFT_OFFSET_KEY_PREFIX = "mfa:totp:drift:";
    private static final int MAX_DRIFT_STEPS = 2;

    private final MfaProperties mfaProperties;
    private final RedisTemplate<String, Object> redisTemplate;
    private final SecureRandom secureRandom = new SecureRandom();

    @Override
    public TotpSetupResponse generateSecret(String username, String issuer) {
        try {
            byte[] secretBytes = new byte[20];
            secureRandom.nextBytes(secretBytes);
            Base32 base32 = new Base32();
            String secret = base32.encodeToString(secretBytes).replaceAll("=", "");

            String qrCodeUri = getQrCodeUri(secret, username, issuer);
            String qrCodeBase64 = generateQrCodeBase64(qrCodeUri);

            return TotpSetupResponse.builder()
                    .secret(secret)
                    .qrCodeUri(qrCodeUri)
                    .qrCodeBase64(qrCodeBase64)
                    .digits(mfaProperties.getTotp().getDigits())
                    .timeStep(mfaProperties.getTotp().getTimeStep())
                    .build();
        } catch (Exception e) {
            log.error("Failed to generate TOTP secret", e);
            throw new RuntimeException("Failed to generate TOTP secret", e);
        }
    }

    @Override
    public boolean verifyCode(String secret, String code) {
        TotpVerificationResult result = verifyCodeWithDrift(secret, code, null);
        return result.isValid();
    }

    @Override
    public TotpVerificationResult verifyCodeWithDrift(String secret, String code, String userId) {
        try {
            Base32 base32 = new Base32();
            byte[] secretBytes = base32.decode(secret);
            SecretKey secretKey = new SecretKeySpec(secretBytes, "AES");

            int timeStep = mfaProperties.getTotp().getTimeStep();
            int digits = mfaProperties.getTotp().getDigits();
            int configuredWindowSize = mfaProperties.getTotp().getWindowSize();

            TimeBasedOneTimePasswordGenerator totpGenerator = new TimeBasedOneTimePasswordGenerator(
                    Duration.ofSeconds(timeStep),
                    digits,
                    TimeBasedOneTimePasswordGenerator.TOTP_ALGORITHM_HMAC_SHA1
            );

            int driftOffset = 0;
            if (userId != null) {
                Integer storedDrift = (Integer) redisTemplate.opsForValue().get(DRIFT_OFFSET_KEY_PREFIX + userId);
                if (storedDrift != null) {
                    driftOffset = storedDrift;
                    log.debug("Using stored drift offset: {} steps for user: {}", driftOffset, userId);
                }
            }

            int effectiveWindowSize = Math.max(configuredWindowSize, 1);
            Instant now = Instant.now();
            int detectedDrift = 0;
            boolean valid = false;

            int totalWindow = effectiveWindowSize + MAX_DRIFT_STEPS;
            for (int i = -totalWindow; i <= totalWindow; i++) {
                int actualOffset = i + driftOffset;
                Instant time = now.plusSeconds((long) actualOffset * timeStep);
                String generatedCode = String.format("%0" + digits + "d",
                        totpGenerator.generateOneTimePassword(secretKey, time));
                if (generatedCode.equals(code)) {
                    valid = true;
                    detectedDrift = actualOffset;
                    log.debug("TOTP code verified successfully with drift offset: {} steps", actualOffset);
                    break;
                }
            }

            if (valid && userId != null && detectedDrift != 0) {
                updateDriftOffset(userId, detectedDrift, driftOffset);
            }

            if (!valid) {
                log.debug("TOTP code verification failed, tried drift range: {} to {}",
                        (-totalWindow + driftOffset), (totalWindow + driftOffset));
            }

            return TotpVerificationResult.builder()
                    .valid(valid)
                    .driftOffset(detectedDrift)
                    .timeStep(timeStep)
                    .serverTime(now.toString())
                    .build();

        } catch (Exception e) {
            log.error("TOTP verification error", e);
            return TotpVerificationResult.builder()
                    .valid(false)
                    .errorMessage(e.getMessage())
                    .build();
        }
    }

    @Override
    public int getCurrentDriftOffset(String userId) {
        if (userId == null) {
            return 0;
        }
        Integer drift = (Integer) redisTemplate.opsForValue().get(DRIFT_OFFSET_KEY_PREFIX + userId);
        return drift != null ? drift : 0;
    }

    @Override
    public void resetDriftOffset(String userId) {
        if (userId != null) {
            redisTemplate.delete(DRIFT_OFFSET_KEY_PREFIX + userId);
            log.info("Reset drift offset for user: {}", userId);
        }
    }

    private void updateDriftOffset(String userId, int detectedDrift, int currentDrift) {
        if (Math.abs(detectedDrift) > MAX_DRIFT_STEPS) {
            log.warn("Drift offset {} exceeds max allowed {}, not updating", detectedDrift, MAX_DRIFT_STEPS);
            return;
        }

        int newDrift = currentDrift + (int) Math.signum(detectedDrift);
        newDrift = Math.max(-MAX_DRIFT_STEPS, Math.min(MAX_DRIFT_STEPS, newDrift));

        if (newDrift != currentDrift) {
            redisTemplate.opsForValue().set(
                    DRIFT_OFFSET_KEY_PREFIX + userId,
                    newDrift,
                    7,
                    TimeUnit.DAYS
            );
            log.info("Updated drift offset from {} to {} steps for user: {}",
                    currentDrift, newDrift, userId);
        }
    }

    @Override
    public String getQrCodeUri(String secret, String username, String issuer) {
        return String.format("otpauth://totp/%s:%s?secret=%s&issuer=%s&digits=%d&period=%d",
                issuer,
                username,
                secret,
                issuer,
                mfaProperties.getTotp().getDigits(),
                mfaProperties.getTotp().getTimeStep());
    }

    private String generateQrCodeBase64(String qrCodeUri) throws Exception {
        QRCodeWriter qrCodeWriter = new QRCodeWriter();
        BitMatrix bitMatrix = qrCodeWriter.encode(qrCodeUri, BarcodeFormat.QR_CODE, 256, 256);
        BufferedImage bufferedImage = MatrixToImageWriter.toBufferedImage(bitMatrix);

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        javax.imageio.ImageIO.write(bufferedImage, "PNG", baos);
        byte[] imageBytes = baos.toByteArray();

        return "data:image/png;base64," + Base64.getEncoder().encodeToString(imageBytes);
    }
}

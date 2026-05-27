package com.sso.saml2;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.security.cert.CertificateExpiredException;
import java.security.cert.CertificateNotYetValidException;
import java.security.cert.X509Certificate;
import java.time.LocalDateTime;
import java.time.ZoneId;

@Slf4j
@Component
public class StrictSaml2CertificateValidator {

    private static final int MIN_KEY_SIZE = 2048;
    private static final int WARN_DAYS_BEFORE_EXPIRY = 30;

    public CertificateValidationResult validate(X509Certificate certificate, String entityId) {
        CertificateValidationResult result = new CertificateValidationResult();
        result.setEntityId(entityId);

        try {
            certificate.checkValidity();
            result.setValid(true);
            log.info("Certificate validity check passed for: {}", entityId);
        } catch (CertificateExpiredException e) {
            result.setValid(false);
            result.addError("Certificate has expired");
            log.error("Certificate expired for: {}", entityId);
            return result;
        } catch (CertificateNotYetValidException e) {
            result.setValid(false);
            result.addError("Certificate is not yet valid");
            log.error("Certificate not yet valid for: {}", entityId);
            return result;
        }

        validateKeySize(certificate, result, entityId);

        validateAlgorithm(certificate, result, entityId);

        checkExpiryWarning(certificate, result, entityId);

        validateBasicConstraints(certificate, result, entityId);

        if (result.isValid()) {
            log.info("Strict certificate validation passed for: {}", entityId);
        } else {
            log.warn("Strict certificate validation found issues for: {}", entityId);
            result.getErrors().forEach(error -> log.warn("  - {}", error));
        }

        return result;
    }

    private void validateKeySize(X509Certificate certificate, CertificateValidationResult result, String entityId) {
        try {
            java.security.PublicKey publicKey = certificate.getPublicKey();
            if (publicKey instanceof java.security.interfaces.RSAPublicKey rsaKey) {
                int keySize = rsaKey.getModulus().bitLength();
                if (keySize < MIN_KEY_SIZE) {
                    result.setValid(false);
                    result.addError("RSA key size is " + keySize + " bits, minimum required is " + MIN_KEY_SIZE + " bits");
                    log.warn("Weak RSA key size {} for: {}", keySize, entityId);
                } else {
                    log.debug("RSA key size {} bits for: {}", keySize, entityId);
                }
            }
        } catch (Exception e) {
            log.warn("Failed to validate key size for: {}", entityId, e);
        }
    }

    private void validateAlgorithm(X509Certificate certificate, CertificateValidationResult result, String entityId) {
        String algorithm = certificate.getSigAlgName();
        if (algorithm != null) {
            if (algorithm.contains("MD5") || algorithm.contains("SHA1")) {
                result.setValid(false);
                result.addError("Weak signature algorithm: " + algorithm + ". Use SHA-256 or stronger");
                log.warn("Weak algorithm {} for: {}", algorithm, entityId);
            } else {
                log.debug("Signature algorithm: {} for: {}", algorithm, entityId);
            }
        }
    }

    private void checkExpiryWarning(X509Certificate certificate, CertificateValidationResult result, String entityId) {
        try {
            LocalDateTime expiryDate = certificate.getNotAfter().toInstant()
                    .atZone(ZoneId.systemDefault())
                    .toLocalDateTime();
            LocalDateTime warningDate = LocalDateTime.now().plusDays(WARN_DAYS_BEFORE_EXPIRY);

            if (expiryDate.isBefore(warningDate)) {
                long daysUntilExpiry = java.time.Duration.between(LocalDateTime.now(), expiryDate).toDays();
                result.addWarning("Certificate expires in " + daysUntilExpiry + " days (" + expiryDate + ")");
                log.warn("Certificate expiry warning for {}: expires in {} days", entityId, daysUntilExpiry);
            }
        } catch (Exception e) {
            log.debug("Could not check expiry warning for: {}", entityId);
        }
    }

    private void validateBasicConstraints(X509Certificate certificate, CertificateValidationResult result, String entityId) {
        try {
            int basicConstraints = certificate.getBasicConstraints();
            if (basicConstraints == -1) {
                log.debug("No BasicConstraints extension for: {}", entityId);
            } else if (basicConstraints == Integer.MAX_VALUE) {
                result.addWarning("Certificate has CA:TRUE with no path length constraint");
                log.warn("Unconstrained CA certificate for: {}", entityId);
            }
        } catch (Exception e) {
            log.debug("Could not validate BasicConstraints for: {}", entityId);
        }
    }

    public static class CertificateValidationResult {
        private String entityId;
        private boolean valid = true;
        private java.util.List<String> errors = new java.util.ArrayList<>();
        private java.util.List<String> warnings = new java.util.ArrayList<>();

        public String getEntityId() { return entityId; }
        public void setEntityId(String entityId) { this.entityId = entityId; }

        public boolean isValid() { return valid; }
        public void setValid(boolean valid) { this.valid = valid; }

        public java.util.List<String> getErrors() { return errors; }
        public void addError(String error) { this.errors.add(error); }

        public java.util.List<String> getWarnings() { return warnings; }
        public void addWarning(String warning) { this.warnings.add(warning); }
    }
}

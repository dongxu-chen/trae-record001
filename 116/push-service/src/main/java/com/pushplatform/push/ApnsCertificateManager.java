package com.pushplatform.push;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.KeyStore;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;
import java.util.concurrent.atomic.AtomicReference;

@Component
public class ApnsCertificateManager {

    private static final Logger logger = LoggerFactory.getLogger(ApnsCertificateManager.class);

    @Value("${push.apns.cert-path:}")
    private String certPath;

    @Value("${push.apns.cert-password:}")
    private String certPassword;

    @Value("${push.apns.alert-days-before-expiry:7}")
    private int alertDaysBeforeExpiry;

    private final AtomicReference<X509Certificate> currentCertificate = new AtomicReference<>();
    private final AtomicReference<LocalDateTime> certificateExpiryDate = new AtomicReference<>();
    private final AtomicReference<Boolean> certificateValid = new AtomicReference<>(false);

    @PostConstruct
    public void init() {
        logger.info("APNS certificate manager initializing...");
        loadCertificate();
    }

    public void loadCertificate() {
        try {
            if (certPath == null || certPath.isEmpty()) {
                logger.warn("APNS certificate path not configured");
                return;
            }

            Path path = Paths.get(certPath);
            if (!Files.exists(path)) {
                logger.error("APNS certificate file not found: {}", certPath);
                certificateValid.set(false);
                return;
            }

            X509Certificate certificate = loadCertificateFromFile(path);
            if (certificate != null) {
                currentCertificate.set(certificate);
                Date expiryDate = certificate.getNotAfter();
                certificateExpiryDate.set(LocalDateTime.ofInstant(expiryDate.toInstant(), ZoneId.systemDefault()));
                certificateValid.set(true);
                
                logger.info("APNS certificate loaded successfully, expiry date: {}", certificateExpiryDate.get());
                
                checkCertificateExpiry();
            }
        } catch (Exception e) {
            logger.error("Failed to load APNS certificate", e);
            certificateValid.set(false);
        }
    }

    private X509Certificate loadCertificateFromFile(Path path) throws Exception {
        String fileName = path.getFileName().toString().toLowerCase();
        
        if (fileName.endsWith(".p12") || fileName.endsWith(".pfx")) {
            KeyStore keyStore = KeyStore.getInstance("PKCS12");
            try (InputStream is = new FileInputStream(path.toFile())) {
                keyStore.load(is, certPassword != null ? certPassword.toCharArray() : null);
                String alias = keyStore.aliases().nextElement();
                return (X509Certificate) keyStore.getCertificate(alias);
            }
        } else if (fileName.endsWith(".pem") || fileName.endsWith(".cer")) {
            CertificateFactory cf = CertificateFactory.getInstance("X.509");
            try (InputStream is = new FileInputStream(path.toFile())) {
                return (X509Certificate) cf.generateCertificate(is);
            }
        } else {
            throw new IllegalArgumentException("Unsupported certificate format: " + fileName);
        }
    }

    @Scheduled(cron = "0 0 9 * * ?")
    public void checkCertificateExpiry() {
        try {
            X509Certificate cert = currentCertificate.get();
            if (cert == null) {
                logger.warn("No APNS certificate loaded");
                return;
            }

            LocalDateTime expiry = certificateExpiryDate.get();
            if (expiry == null) {
                return;
            }

            LocalDateTime now = LocalDateTime.now();
            long daysUntilExpiry = java.time.Duration.between(now, expiry).toDays();

            logger.info("APNS certificate days until expiry: {}", daysUntilExpiry);

            if (daysUntilExpiry <= 0) {
                logger.error("ALERT: APNS certificate has expired! Expiry date: {}", expiry);
                sendAlert("APNS证书已过期，请立即更新！过期时间: " + expiry);
            } else if (daysUntilExpiry <= alertDaysBeforeExpiry) {
                logger.warn("ALERT: APNS certificate will expire in {} days! Expiry date: {}", 
                        daysUntilExpiry, expiry);
                sendAlert("APNS证书将在 " + daysUntilExpiry + " 天后过期，请及时更新！过期时间: " + expiry);
            }
        } catch (Exception e) {
            logger.error("Failed to check certificate expiry", e);
        }
    }

    private void sendAlert(String message) {
        logger.error("APNS CERTIFICATE ALERT: {}", message);
    }

    public boolean reloadCertificate() {
        try {
            logger.info("Reloading APNS certificate...");
            loadCertificate();
            logger.info("APNS certificate reload completed, valid: {}", certificateValid.get());
            return certificateValid.get();
        } catch (Exception e) {
            logger.error("Failed to reload APNS certificate", e);
            return false;
        }
    }

    public boolean isCertificateValid() {
        return certificateValid.get();
    }

    public LocalDateTime getCertificateExpiryDate() {
        return certificateExpiryDate.get();
    }

    public long getDaysUntilExpiry() {
        LocalDateTime expiry = certificateExpiryDate.get();
        if (expiry == null) {
            return -1;
        }
        return java.time.Duration.between(LocalDateTime.now(), expiry).toDays();
    }
}

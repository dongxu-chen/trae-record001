package com.sso.util;

import lombok.extern.slf4j.Slf4j;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cert.X509v3CertificateBuilder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.operator.ContentSigner;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;

import java.io.*;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.*;
import java.security.cert.X509Certificate;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Base64;
import java.util.Date;

@Slf4j
public class CertificateGenerator {

    private static final String BEGIN_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----";
    private static final String END_PRIVATE_KEY = "-----END PRIVATE KEY-----";
    private static final String BEGIN_CERT = "-----BEGIN CERTIFICATE-----";
    private static final String END_CERT = "-----END CERTIFICATE-----";

    static {
        if (Security.getProvider(BouncyCastleProvider.PROVIDER_NAME) == null) {
            Security.addProvider(new BouncyCastleProvider());
        }
    }

    public static void main(String[] args) {
        try {
            String outputDir = args.length > 0 ? args[0] : "src/main/resources/credentials";
            generateAllCertificates(outputDir);
        } catch (Exception e) {
            log.error("Failed to generate certificates", e);
            System.exit(1);
        }
    }

    public static void generateAllCertificates(String outputDir) throws Exception {
        Files.createDirectories(Paths.get(outputDir));

        log.info("Generating OAuth2 JWT keystore...");
        generateOAuth2Keystore(outputDir + "/oauth2.jks");

        log.info("Generating SAML2 signing key pair...");
        generateRsaKeyPair(outputDir + "/saml-signing.key", outputDir + "/saml-signing.crt", "sso.example.com");

        log.info("Generating SAML2 encryption key pair...");
        generateRsaKeyPair(outputDir + "/saml-encryption.key", outputDir + "/saml-encryption.crt", "sso.example.com");

        log.info("All certificates generated successfully in: {}", outputDir);
    }

    public static void generateOAuth2Keystore(String keystorePath) throws Exception {
        char[] password = "changeit".toCharArray();
        String alias = "oauth2-key";

        KeyStore keyStore = KeyStore.getInstance("JKS");
        keyStore.load(null, password);

        KeyPair keyPair = generateRsaKeyPair(2048);
        X509Certificate cert = generateSelfSignedCertificate(keyPair, "CN=SSO Server, OU=IT, O=Company, L=City, ST=State, C=CN", 3650);

        keyStore.setKeyEntry(alias, keyPair.getPrivate(), password, new java.security.cert.Certificate[]{cert});

        try (FileOutputStream fos = new FileOutputStream(keystorePath)) {
            keyStore.store(fos, password);
        }

        log.info("OAuth2 keystore generated: {}", keystorePath);
    }

    public static void generateRsaKeyPair(String keyPath, String certPath, String commonName) throws Exception {
        KeyPair keyPair = generateRsaKeyPair(2048);
        X509Certificate cert = generateSelfSignedCertificate(keyPair,
                "C=CN, ST=State, L=City, O=Company, OU=IT, CN=" + commonName, 3650);

        writePrivateKey(keyPair.getPrivate(), keyPath);
        writeCertificate(cert, certPath);

        log.info("RSA key pair generated: {} and {}", keyPath, certPath);
    }

    private static KeyPair generateRsaKeyPair(int keySize) throws NoSuchAlgorithmException {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
        keyGen.initialize(keySize, new SecureRandom());
        return keyGen.generateKeyPair();
    }

    private static X509Certificate generateSelfSignedCertificate(KeyPair keyPair, String dn, int days) throws Exception {
        long now = System.currentTimeMillis();
        Date startDate = new Date(now);
        Date endDate = new Date(now + (long) days * 24 * 60 * 60 * 1000);
        BigInteger serialNumber = new BigInteger(64, new SecureRandom());

        X500Name subject = new X500Name(dn);
        X500Name issuer = subject;

        X509v3CertificateBuilder certBuilder = new JcaX509v3CertificateBuilder(
                issuer,
                serialNumber,
                startDate,
                endDate,
                subject,
                keyPair.getPublic()
        );

        ContentSigner signer = new JcaContentSignerBuilder("SHA256withRSA")
                .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                .build(keyPair.getPrivate());

        X509CertificateHolder certHolder = certBuilder.build(signer);
        return new JcaX509CertificateConverter()
                .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                .getCertificate(certHolder);
    }

    private static void writePrivateKey(PrivateKey privateKey, String path) throws Exception {
        PKCS8EncodedKeySpec spec = new PKCS8EncodedKeySpec(privateKey.getEncoded());
        String encoded = Base64.getMimeEncoder(64, new byte[]{'\n'}).encodeToString(spec.getEncoded());

        StringBuilder sb = new StringBuilder();
        sb.append(BEGIN_PRIVATE_KEY).append("\n");
        sb.append(encoded).append("\n");
        sb.append(END_PRIVATE_KEY).append("\n");

        try (FileWriter fw = new FileWriter(path)) {
            fw.write(sb.toString());
        }
    }

    private static void writeCertificate(X509Certificate cert, String path) throws Exception {
        String encoded = Base64.getMimeEncoder(64, new byte[]{'\n'}).encodeToString(cert.getEncoded());

        StringBuilder sb = new StringBuilder();
        sb.append(BEGIN_CERT).append("\n");
        sb.append(encoded).append("\n");
        sb.append(END_CERT).append("\n");

        try (FileWriter fw = new FileWriter(path)) {
            fw.write(sb.toString());
        }
    }

    public static boolean checkCertificatesExist(String dir) {
        String[] requiredFiles = {"oauth2.jks", "saml-signing.key", "saml-signing.crt"};
        for (String file : requiredFiles) {
            if (!Files.exists(Paths.get(dir, file))) {
                return false;
            }
        }
        return true;
    }
}

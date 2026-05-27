package com.sso.config;

import com.sso.auth.saml2.Saml2AuthenticationSuccessHandler;
import com.sso.config.properties.SsoProperties;
import com.sso.entity.Saml2Sp;
import com.sso.repository.Saml2SpRepository;
import com.sso.saml2.StrictSaml2CertificateValidator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;
import org.springframework.security.converter.RsaKeyConverters;
import org.springframework.security.saml2.core.Saml2X509Credential;
import org.springframework.security.saml2.provider.service.metadata.OpenSamlMetadataResolver;
import org.springframework.security.saml2.provider.service.registration.InMemoryRelyingPartyRegistrationRepository;
import org.springframework.security.saml2.provider.service.registration.RelyingPartyRegistration;
import org.springframework.security.saml2.provider.service.registration.RelyingPartyRegistrationRepository;
import org.springframework.security.saml2.provider.service.registration.Saml2MessageBinding;

import java.io.InputStream;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.security.interfaces.RSAPrivateKey;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class Saml2Config {

    private final SsoProperties ssoProperties;
    private final Saml2SpRepository spRepository;
    private final Saml2AuthenticationSuccessHandler successHandler;
    private final StrictSaml2CertificateValidator certificateValidator;

    @Bean
    public RelyingPartyRegistrationRepository relyingPartyRegistrationRepository() throws Exception {
        List<RelyingPartyRegistration> registrations = new ArrayList<>();

        Saml2X509Credential signingCredential = getSigningCredential();
        Saml2X509Credential encryptionCredential = getEncryptionCredential();

        initializeDefaultServiceProviders();

        for (Saml2Sp sp : spRepository.findAll()) {
            if (!sp.isEnabled()) {
                continue;
            }

            RelyingPartyRegistration.Builder builder = RelyingPartyRegistration
                    .withRegistrationId(sp.getEntityId())
                    .entityId(ssoProperties.getSaml2().getEntityId())
                    .assertionConsumerServiceLocation(sp.getAssertionConsumerServiceUrl())
                    .singleLogoutServiceLocation(sp.getSingleLogoutServiceUrl())
                    .nameIdFormat(sp.getNameIdFormat())
                    .signingX509Credentials(c -> c.add(signingCredential))
                    .decryptionX509Credentials(c -> c.add(encryptionCredential))
                    .assertingPartyDetails(details -> details
                            .entityId(sp.getEntityId())
                            .singleSignOnServiceLocation(sp.getAssertionConsumerServiceUrl())
                            .singleLogoutServiceLocation(sp.getSingleLogoutServiceUrl())
                            .wantAuthnRequestsSigned(sp.isSignAuthnRequests())
                            .singleSignOnServiceBinding(Saml2MessageBinding.POST)
                            .singleLogoutServiceBinding(Saml2MessageBinding.POST)
                            .verificationX509Credentials(c -> {
                                if (sp.getCertificate() != null && !sp.getCertificate().isEmpty()) {
                                    try {
                                        X509Certificate cert = parseCertificate(sp.getCertificate());
                                        
                                        StrictSaml2CertificateValidator.CertificateValidationResult validationResult = 
                                                certificateValidator.validate(cert, sp.getEntityId());
                                        
                                        if (!validationResult.isValid()) {
                                            log.error("Certificate validation failed for SP {}: {}", 
                                                    sp.getEntityId(), validationResult.getErrors());
                                            throw new RuntimeException("Certificate validation failed for " + sp.getEntityId());
                                        }
                                        
                                        if (!validationResult.getWarnings().isEmpty()) {
                                            log.warn("Certificate warnings for SP {}: {}", 
                                                    sp.getEntityId(), validationResult.getWarnings());
                                        }
                                        
                                        c.add(Saml2X509Credential.verification(cert));
                                        log.info("Certificate validated successfully for SP: {}", sp.getEntityId());
                                    } catch (Exception e) {
                                        log.error("Failed to parse/validate certificate for SP: {}", sp.getEntityId(), e);
                                        throw new RuntimeException("Certificate validation failed for " + sp.getEntityId(), e);
                                    }
                                }
                            })
                    );

            registrations.add(builder.build());
            log.info("Registered SAML2 Service Provider: {}", sp.getEntityId());
        }

        return new InMemoryRelyingPartyRegistrationRepository(registrations);
    }

    @Bean
    public OpenSamlMetadataResolver saml2MetadataResolver() {
        return new OpenSamlMetadataResolver();
    }

    private Saml2X509Credential getSigningCredential() throws Exception {
        X509Certificate cert = loadCertificate(ssoProperties.getSaml2().getSigningCertLocation());
        RSAPrivateKey key = loadPrivateKey(ssoProperties.getSaml2().getSigningKeyLocation());
        return Saml2X509Credential.signing(key, cert);
    }

    private Saml2X509Credential getEncryptionCredential() throws Exception {
        X509Certificate cert = loadCertificate(ssoProperties.getSaml2().getEncryptionCertLocation());
        RSAPrivateKey key = loadPrivateKey(ssoProperties.getSaml2().getEncryptionKeyLocation());
        return Saml2X509Credential.decryption(key, cert);
    }

    private X509Certificate loadCertificate(String location) throws Exception {
        ClassPathResource resource = new ClassPathResource(location);
        try (InputStream is = resource.getInputStream()) {
            CertificateFactory cf = CertificateFactory.getInstance("X.509");
            return (X509Certificate) cf.generateCertificate(is);
        }
    }

    private RSAPrivateKey loadPrivateKey(String location) throws Exception {
        ClassPathResource resource = new ClassPathResource(location);
        try (InputStream is = resource.getInputStream()) {
            return RsaKeyConverters.pkcs8().convert(is);
        }
    }

    private X509Certificate parseCertificate(String pem) throws Exception {
        String cleanCert = pem
                .replace("-----BEGIN CERTIFICATE-----", "")
                .replace("-----END CERTIFICATE-----", "")
                .replaceAll("\\s", "");

        byte[] decoded = java.util.Base64.getDecoder().decode(cleanCert);
        CertificateFactory cf = CertificateFactory.getInstance("X.509");
        return (X509Certificate) cf.generateCertificate(new java.io.ByteArrayInputStream(decoded));
    }

    private void initializeDefaultServiceProviders() {
        if (spRepository.count() == 0) {
            Saml2Sp defaultSp = new Saml2Sp();
            defaultSp.setEntityId("https://sp.example.com/saml2");
            defaultSp.setSpName("Example Service Provider");
            defaultSp.setAssertionConsumerServiceUrl("https://sp.example.com/saml2/acs");
            defaultSp.setSingleLogoutServiceUrl("https://sp.example.com/saml2/slo");
            defaultSp.setNameIdFormat("urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress");
            defaultSp.setSignAuthnRequests(true);
            defaultSp.setEncryptAssertions(false);
            defaultSp.setEnabled(true);
            defaultSp.setDescription("Default test service provider");
            spRepository.save(defaultSp);
            log.info("Created default SAML2 Service Provider: {}", defaultSp.getEntityId());
        }
    }
}

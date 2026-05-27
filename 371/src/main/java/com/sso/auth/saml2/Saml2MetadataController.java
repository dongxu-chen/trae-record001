package com.sso.auth.saml2;

import com.sso.config.properties.SsoProperties;
import com.sso.entity.Saml2Sp;
import com.sso.repository.Saml2SpRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.saml2.provider.service.registration.RelyingPartyRegistration;
import org.springframework.security.saml2.provider.service.registration.RelyingPartyRegistrationRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.StringWriter;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/saml2")
@RequiredArgsConstructor
public class Saml2MetadataController {

    private final SsoProperties ssoProperties;
    private final Saml2SpRepository spRepository;
    private final RelyingPartyRegistrationRepository relyingPartyRegistrationRepository;

    @GetMapping("/metadata/{registrationId}")
    public Map<String, Object> getMetadata(@PathVariable String registrationId) {
        Map<String, Object> metadata = new HashMap<>();

        RelyingPartyRegistration registration = relyingPartyRegistrationRepository.findByRegistrationId(registrationId);
        Saml2Sp sp = spRepository.findByEntityId(registrationId).orElse(null);

        if (registration != null) {
            metadata.put("entityId", registration.getEntityId());
            metadata.put("registrationId", registration.getRegistrationId());
            metadata.put("assertionConsumerServiceUrl", registration.getAssertionConsumerServiceLocation());
            metadata.put("singleLogoutServiceUrl", registration.getSingleLogoutServiceLocation());
            metadata.put("nameIdFormat", registration.getNameIdFormat());
            metadata.put("signAuthnRequests",
                    registration.getAssertingPartyDetails().getWantAuthnRequestsSigned());
        }

        if (sp != null) {
            metadata.put("spName", sp.getSpName());
            metadata.put("description", sp.getDescription());
            metadata.put("logoUrl", sp.getLogoUrl());
            metadata.put("enabled", sp.isEnabled());
        }

        metadata.put("idpEntityId", ssoProperties.getSaml2().getEntityId());
        metadata.put("idpSsoUrl", ssoProperties.getSaml2().getBaseUrl() + "/saml2/authenticate/" + registrationId);
        metadata.put("idpSloUrl", ssoProperties.getSaml2().getBaseUrl() + "/saml2/slo/" + registrationId);
        metadata.put("idpMetadataUrl", ssoProperties.getSaml2().getBaseUrl() + "/saml2/metadata/" + registrationId);

        return metadata;
    }

    @GetMapping("/metadata")
    public Map<String, Object> getIdpMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("entityId", ssoProperties.getSaml2().getEntityId());
        metadata.put("ssoUrl", ssoProperties.getSaml2().getBaseUrl() + "/saml2/authenticate");
        metadata.put("sloUrl", ssoProperties.getSaml2().getBaseUrl() + "/saml2/slo");
        metadata.put("metadataUrl", ssoProperties.getSaml2().getBaseUrl() + "/saml2/metadata");
        metadata.put("nameIdFormats", new String[]{
                "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
                "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent",
                "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
        });
        metadata.put("supportedBindings", new String[]{
                "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        });
        return metadata;
    }
}

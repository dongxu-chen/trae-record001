package com.sso.auth.saml2;

import com.sso.config.properties.SsoProperties;
import com.sso.entity.User;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.saml2.core.Saml2ParameterNames;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class Saml2ResponseGenerator {

    private final SsoProperties ssoProperties;

    public Map<String, String> generateAuthnResponse(User user, String destination, String inResponseTo) {
        Map<String, String> response = new HashMap<>();

        String responseId = "_" + UUID.randomUUID().toString();
        String assertionId = "_" + UUID.randomUUID().toString();
        Instant now = Instant.now();
        Instant notOnOrAfter = now.plus(1, ChronoUnit.HOURS);

        String samlResponse = buildSamlResponse(
                responseId,
                assertionId,
                user,
                destination,
                inResponseTo,
                now,
                notOnOrAfter
        );

        String encodedResponse = java.util.Base64.getEncoder()
                .encodeToString(samlResponse.getBytes(StandardCharsets.UTF_8));

        response.put(Saml2ParameterNames.SAML_RESPONSE, encodedResponse);
        response.put("RelayState", destination);
        response.put("Destination", destination);

        return response;
    }

    private String buildSamlResponse(String responseId, String assertionId, User user,
                                     String destination, String inResponseTo,
                                     Instant now, Instant notOnOrAfter) {
        String issuer = ssoProperties.getSaml2().getEntityId();
        String nameId = user.getUsername();

        return """
                <saml2p:Response xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol"
                                 xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion"
                                 ID="%s"
                                 Version="2.0"
                                 IssueInstant="%s"
                                 Destination="%s"
                                 %s>
                    <saml2:Issuer>%s</saml2:Issuer>
                    <saml2p:Status>
                        <saml2p:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
                    </saml2p:Status>
                    <saml2:Assertion xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion"
                                     ID="%s"
                                     IssueInstant="%s"
                                     Version="2.0">
                        <saml2:Issuer>%s</saml2:Issuer>
                        <saml2:Subject>
                            <saml2:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified">%s</saml2:NameID>
                            <saml2:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                                <saml2:SubjectConfirmationData NotOnOrAfter="%s"
                                                               Recipient="%s"
                                                               %s/>
                            </saml2:SubjectConfirmation>
                        </saml2:Subject>
                        <saml2:Conditions NotBefore="%s" NotOnOrAfter="%s">
                            <saml2:AudienceRestriction>
                                <saml2:Audience>%s</saml2:Audience>
                            </saml2:AudienceRestriction>
                        </saml2:Conditions>
                        <saml2:AuthnStatement AuthnInstant="%s" SessionIndex="%s">
                            <saml2:AuthnContext>
                                <saml2:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml2:AuthnContextClassRef>
                            </saml2:AuthnContext>
                        </saml2:AuthnStatement>
                        <saml2:AttributeStatement>
                            <saml2:Attribute Name="email">
                                <saml2:AttributeValue xmlns:xs="http://www.w3.org/2001/XMLSchema"
                                                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                                      xsi:type="xs:string">%s</saml2:AttributeValue>
                            </saml2:Attribute>
                            <saml2:Attribute Name="firstName">
                                <saml2:AttributeValue xmlns:xs="http://www.w3.org/2001/XMLSchema"
                                                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                                      xsi:type="xs:string">%s</saml2:AttributeValue>
                            </saml2:Attribute>
                            <saml2:Attribute Name="lastName">
                                <saml2:AttributeValue xmlns:xs="http://www.w3.org/2001/XMLSchema"
                                                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                                      xsi:type="xs:string">%s</saml2:AttributeValue>
                            </saml2:Attribute>
                        </saml2:AttributeStatement>
                    </saml2:Assertion>
                </saml2p:Response>
                """.formatted(
                responseId,
                now.toString(),
                destination,
                inResponseTo != null ? "InResponseTo=\"" + inResponseTo + "\"" : "",
                issuer,
                assertionId,
                now.toString(),
                issuer,
                nameId,
                notOnOrAfter.toString(),
                destination,
                inResponseTo != null ? "InResponseTo=\"" + inResponseTo + "\"" : "",
                now.toString(),
                notOnOrAfter.toString(),
                destination,
                now.toString(),
                "_" + UUID.randomUUID().toString(),
                user.getEmail() != null ? user.getEmail() : user.getUsername() + "@local",
                user.getFirstName() != null ? user.getFirstName() : "",
                user.getLastName() != null ? user.getLastName() : ""
        );
    }
}

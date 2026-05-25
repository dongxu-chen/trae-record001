package com.mfa.service.impl;

import com.mfa.config.MfaProperties;
import com.mfa.dto.WebAuthnAssertion;
import com.mfa.dto.WebAuthnCredential;
import com.mfa.dto.WebAuthnOptionsResponse;
import com.mfa.entity.AuthFactor;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import com.mfa.repository.AuthFactorRepository;
import com.mfa.repository.UserRepository;
import com.mfa.service.WebAuthnService;
import com.webauthn4j.WebAuthnManager;
import com.webauthn4j.authenticator.Authenticator;
import com.webauthn4j.authenticator.AuthenticatorImpl;
import com.webauthn4j.converter.util.ObjectConverter;
import com.webauthn4j.data.*;
import com.webauthn4j.data.attestation.statement.COSEAlgorithmIdentifier;
import com.webauthn4j.data.client.Origin;
import com.webauthn4j.data.client.challenge.Challenge;
import com.webauthn4j.data.client.challenge.DefaultChallenge;
import com.webauthn4j.data.extension.client.AuthenticationExtensionClientInput;
import com.webauthn4j.data.extension.client.CredentialPropertiesExtensionClientInput;
import com.webauthn4j.server.ServerProperty;
import com.webauthn4j.validator.exception.ValidationException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class WebAuthnServiceImpl implements WebAuthnService {

    private static final String CHALLENGE_KEY_PREFIX = "mfa:webauthn:challenge:";
    private static final int CHALLENGE_EXPIRE_MINUTES = 5;
    private static final String PASSKEY_CHALLENGE_KEY_PREFIX = "mfa:passkey:challenge:";

    private final MfaProperties mfaProperties;
    private final AuthFactorRepository authFactorRepository;
    private final UserRepository userRepository;
    private final RedisTemplate<String, Object> redisTemplate;

    private final ObjectConverter objectConverter = new ObjectConverter();
    private final WebAuthnManager webAuthnManager = WebAuthnManager.createNonStrictWebAuthnManager(objectConverter);

    @Override
    public WebAuthnOptionsResponse generateRegistrationOptions(String sessionId, User user) {
        Challenge challenge = new DefaultChallenge();
        storeChallenge(sessionId, challenge);

        PublicKeyCredentialUserEntity userEntity = new PublicKeyCredentialUserEntity(
                user.getUsername(),
                user.getId().toString().getBytes(),
                user.getUsername()
        );

        PublicKeyCredentialCreationOptions options = new PublicKeyCredentialCreationOptions(
                new PublicKeyCredentialRpEntity(
                        mfaProperties.getWebauthn().getRelyingPartyId(),
                        mfaProperties.getWebauthn().getRelyingPartyName()
                ),
                userEntity,
                challenge,
                Collections.singletonList(new PublicKeyCredentialParameters(
                        PublicKeyCredentialType.PUBLIC_KEY,
                        COSEAlgorithmIdentifier.ES256
                )),
                60000L,
                null,
                Collections.emptyList(),
                new AuthenticatorSelectionCriteria(
                        AuthenticatorAttachment.CROSS_PLATFORM,
                        true,
                        UserVerificationRequirement.PREFERRED
                ),
                AttestationConveyancePreference.NONE,
                null
        );

        return WebAuthnOptionsResponse.builder()
                .challenge(Base64.getUrlEncoder().withoutPadding().encodeToString(challenge.getValue()))
                .registrationOptions(options)
                .build();
    }

    @Override
    public boolean verifyRegistration(String sessionId, WebAuthnCredential credential, User user) {
        try {
            Challenge challenge = getStoredChallenge(sessionId);
            if (challenge == null) {
                log.warn("No challenge found for session: {}", sessionId);
                return false;
            }

            byte[] credentialId = Base64.getUrlDecoder().decode(credential.getRawId());
            byte[] clientDataJSON = Base64.getUrlDecoder().decode(credential.getResponse().getClientDataJSON());
            byte[] attestationObject = Base64.getUrlDecoder().decode(credential.getResponse().getAttestationObject());

            Origin origin = Origin.create(mfaProperties.getWebauthn().getOrigin());
            String rpId = mfaProperties.getWebauthn().getRelyingPartyId();

            ServerProperty serverProperty = new ServerProperty(origin, rpId, challenge, null);

            RegistrationRequest registrationRequest = new RegistrationRequest(
                    credentialId,
                    user.getId().toString().getBytes(),
                    clientDataJSON,
                    attestationObject,
                    null,
                    null
            );

            RegistrationParameters registrationParameters = new RegistrationParameters(
                    serverProperty,
                    null,
                    false,
                    true
            );

            RegistrationData registrationData = webAuthnManager.parse(registrationRequest);
            webAuthnManager.validate(registrationData, registrationParameters);

            Authenticator authenticator = new AuthenticatorImpl(
                    registrationData.getAttestationObject().getAuthenticatorData().getAttestedCredentialData(),
                    registrationData.getAttestationObject().getAttestationStatement(),
                    registrationData.getAttestationObject().getAuthenticatorData().getSignCount()
            );

            AuthFactor authFactor = new AuthFactor();
            authFactor.setUser(user);
            authFactor.setFactorType(FactorType.WEBAUTHN);
            authFactor.setName("Hardware Key");
            authFactor.setCredentialId(Base64.getUrlEncoder().withoutPadding().encodeToString(
                    authenticator.getAttestedCredentialData().getCredentialId()));
            authFactor.setPublicKey(Base64.getEncoder().encodeToString(
                    authenticator.getAttestedCredentialData().getCredentialPublicKey()));
            authFactor.setSignCount(authenticator.getSignCount());
            authFactor.setAaguid(authenticator.getAttestedCredentialData().getAaguid().toString());
            authFactor.setVerified(true);
            authFactor.setEnabled(true);

            authFactorRepository.save(authFactor);

            removeChallenge(sessionId);
            log.info("WebAuthn registration verified successfully for user: {}", user.getUsername());
            return true;

        } catch (ValidationException e) {
            log.error("WebAuthn registration validation failed", e);
            return false;
        } catch (Exception e) {
            log.error("WebAuthn registration error", e);
            return false;
        }
    }

    @Override
    public WebAuthnOptionsResponse generateAuthenticationOptions(String sessionId, User user) {
        Challenge challenge = new DefaultChallenge();
        storeChallenge(sessionId, challenge);

        List<AuthFactor> webAuthnFactors = authFactorRepository.findByUserIdAndFactorType(
                user.getId(), FactorType.WEBAUTHN);

        List<PublicKeyCredentialDescriptor> allowedCredentials = new ArrayList<>();
        for (AuthFactor factor : webAuthnFactors) {
            if (factor.isVerified() && factor.isEnabled()) {
                byte[] credentialId = Base64.getUrlDecoder().decode(factor.getCredentialId());
                allowedCredentials.add(new PublicKeyCredentialDescriptor(
                        PublicKeyCredentialType.PUBLIC_KEY,
                        credentialId,
                        Collections.singletonList(AuthenticatorTransport.USB)
                ));
            }
        }

        PublicKeyCredentialRequestOptions options = new PublicKeyCredentialRequestOptions(
                challenge,
                60000L,
                mfaProperties.getWebauthn().getRelyingPartyId(),
                allowedCredentials,
                UserVerificationRequirement.PREFERRED,
                null
        );

        return WebAuthnOptionsResponse.builder()
                .challenge(Base64.getUrlEncoder().withoutPadding().encodeToString(challenge.getValue()))
                .authenticationOptions(options)
                .build();
    }

    @Override
    public boolean verifyAuthentication(String sessionId, WebAuthnAssertion assertion, User user) {
        try {
            Challenge challenge = getStoredChallenge(sessionId);
            if (challenge == null) {
                log.warn("No challenge found for session: {}", sessionId);
                return false;
            }

            byte[] credentialId = Base64.getUrlDecoder().decode(assertion.getRawId());
            byte[] clientDataJSON = Base64.getUrlDecoder().decode(assertion.getResponse().getClientDataJSON());
            byte[] authenticatorData = Base64.getUrlDecoder().decode(assertion.getResponse().getAuthenticatorData());
            byte[] signature = Base64.getUrlDecoder().decode(assertion.getResponse().getSignature());

            String credentialIdStr = Base64.getUrlEncoder().withoutPadding().encodeToString(credentialId);
            AuthFactor authFactor = authFactorRepository.findByCredentialId(credentialIdStr)
                    .orElseThrow(() -> new IllegalArgumentException("Unknown credential"));

            if (!authFactor.getUser().getId().equals(user.getId())) {
                log.warn("Credential does not belong to user: {}", user.getUsername());
                return false;
            }

            byte[] publicKey = Base64.getDecoder().decode(authFactor.getPublicKey());
            long signCount = authFactor.getSignCount() != null ? authFactor.getSignCount() : 0L;

            Authenticator authenticator = new AuthenticatorImpl(
                    null,
                    publicKey,
                    signCount
            );

            Origin origin = Origin.create(mfaProperties.getWebauthn().getOrigin());
            String rpId = mfaProperties.getWebauthn().getRelyingPartyId();

            ServerProperty serverProperty = new ServerProperty(origin, rpId, challenge, null);

            AuthenticationRequest authenticationRequest = new AuthenticationRequest(
                    credentialId,
                    user.getId().toString().getBytes(),
                    authenticatorData,
                    clientDataJSON,
                    signature,
                    null
            );

            AuthenticationParameters authenticationParameters = new AuthenticationParameters(
                    serverProperty,
                    authenticator,
                    false,
                    true
            );

            AuthenticationData authenticationData = webAuthnManager.parse(authenticationRequest);
            webAuthnManager.validate(authenticationData, authenticationParameters);

            authFactor.setSignCount(authenticationData.getAuthenticatorData().getSignCount());
            authFactor.setLastUsedAt(java.time.LocalDateTime.now());
            authFactorRepository.save(authFactor);

            removeChallenge(sessionId);
            log.info("WebAuthn authentication verified successfully for user: {}", user.getUsername());
            return true;

        } catch (ValidationException e) {
            log.error("WebAuthn authentication validation failed", e);
            return false;
        } catch (Exception e) {
            log.error("WebAuthn authentication error", e);
            return false;
        }
    }

    private void storeChallenge(String sessionId, Challenge challenge) {
        String key = CHALLENGE_KEY_PREFIX + sessionId;
        redisTemplate.opsForValue().set(key, challenge.getValue(), CHALLENGE_EXPIRE_MINUTES, TimeUnit.MINUTES);
    }

    private Challenge getStoredChallenge(String sessionId) {
        String key = CHALLENGE_KEY_PREFIX + sessionId;
        byte[] value = (byte[]) redisTemplate.opsForValue().get(key);
        if (value == null) {
            return null;
        }
        return new DefaultChallenge(value);
    }

    private void removeChallenge(String sessionId) {
        String key = CHALLENGE_KEY_PREFIX + sessionId;
        redisTemplate.delete(key);
    }

    @Override
    public WebAuthnOptionsResponse generatePasskeyRegistrationOptions(String sessionId, User user) {
        Challenge challenge = new DefaultChallenge();
        storePasskeyChallenge(sessionId, challenge);

        PublicKeyCredentialUserEntity userEntity = new PublicKeyCredentialUserEntity(
                user.getUsername(),
                user.getId().toString().getBytes(StandardCharsets.UTF_8),
                user.getUsername()
        );

        List<PublicKeyCredentialParameters> pubKeyCredParams = Arrays.asList(
                new PublicKeyCredentialParameters(PublicKeyCredentialType.PUBLIC_KEY, COSEAlgorithmIdentifier.ES256),
                new PublicKeyCredentialParameters(PublicKeyCredentialType.PUBLIC_KEY, COSEAlgorithmIdentifier.RS256),
                new PublicKeyCredentialParameters(PublicKeyCredentialType.PUBLIC_KEY, COSEAlgorithmIdentifier.EdDSA)
        );

        AuthenticatorSelectionCriteria authenticatorSelection = new AuthenticatorSelectionCriteria(
                null,
                true,
                UserVerificationRequirement.REQUIRED
        );

        Map<String, AuthenticationExtensionClientInput<?>> extensions = new HashMap<>();
        extensions.put("credProps", new CredentialPropertiesExtensionClientInput(true));

        PublicKeyCredentialCreationOptions options = new PublicKeyCredentialCreationOptions(
                new PublicKeyCredentialRpEntity(
                        mfaProperties.getWebauthn().getRelyingPartyId(),
                        mfaProperties.getWebauthn().getRelyingPartyName()
                ),
                userEntity,
                challenge,
                pubKeyCredParams,
                120000L,
                null,
                Collections.emptyList(),
                authenticatorSelection,
                AttestationConveyancePreference.NONE,
                extensions
        );

        log.info("Generated passkey registration options for user: {}", user.getUsername());

        return WebAuthnOptionsResponse.builder()
                .challenge(Base64.getUrlEncoder().withoutPadding().encodeToString(challenge.getValue()))
                .registrationOptions(options)
                .build();
    }

    @Override
    public WebAuthnOptionsResponse generatePasskeyAuthenticationOptions(String sessionId) {
        Challenge challenge = new DefaultChallenge();
        storePasskeyChallenge(sessionId, challenge);

        Map<String, AuthenticationExtensionClientInput<?>> extensions = new HashMap<>();

        PublicKeyCredentialRequestOptions options = new PublicKeyCredentialRequestOptions(
                challenge,
                120000L,
                mfaProperties.getWebauthn().getRelyingPartyId(),
                Collections.emptyList(),
                UserVerificationRequirement.REQUIRED,
                extensions
        );

        log.info("Generated passkey authentication options for session: {}", sessionId);

        return WebAuthnOptionsResponse.builder()
                .challenge(Base64.getUrlEncoder().withoutPadding().encodeToString(challenge.getValue()))
                .authenticationOptions(options)
                .build();
    }

    @Override
    public User verifyPasskeyAuthentication(String sessionId, WebAuthnAssertion assertion) {
        try {
            Challenge challenge = getStoredPasskeyChallenge(sessionId);
            if (challenge == null) {
                log.warn("No passkey challenge found for session: {}", sessionId);
                return null;
            }

            byte[] credentialId = Base64.getUrlDecoder().decode(assertion.getRawId());
            byte[] clientDataJSON = Base64.getUrlDecoder().decode(assertion.getResponse().getClientDataJSON());
            byte[] authenticatorData = Base64.getUrlDecoder().decode(assertion.getResponse().getAuthenticatorData());
            byte[] signature = Base64.getUrlDecoder().decode(assertion.getResponse().getSignature());
            byte[] userHandle = assertion.getResponse().getUserHandle() != null
                    ? Base64.getUrlDecoder().decode(assertion.getResponse().getUserHandle())
                    : null;

            String credentialIdStr = Base64.getUrlEncoder().withoutPadding().encodeToString(credentialId);
            AuthFactor authFactor = authFactorRepository.findByCredentialId(credentialIdStr)
                    .orElse(null);

            if (authFactor == null) {
                log.warn("Passkey credential not found: {}", credentialIdStr);
                return null;
            }

            User user = authFactor.getUser();
            if (!authFactor.isEnabled() || authFactor.isRevoked()) {
                log.warn("Passkey credential is disabled or revoked for user: {}", user.getUsername());
                return null;
            }

            byte[] expectedUserHandle = user.getId().toString().getBytes(StandardCharsets.UTF_8);
            if (userHandle != null && !Arrays.equals(userHandle, expectedUserHandle)) {
                log.warn("User handle mismatch for passkey authentication");
                return null;
            }

            byte[] publicKey = Base64.getDecoder().decode(authFactor.getPublicKey());
            long signCount = authFactor.getSignCount() != null ? authFactor.getSignCount() : 0L;

            Authenticator authenticator = new AuthenticatorImpl(
                    null,
                    publicKey,
                    signCount
            );

            Origin origin = Origin.create(mfaProperties.getWebauthn().getOrigin());
            String rpId = mfaProperties.getWebauthn().getRelyingPartyId();

            ServerProperty serverProperty = new ServerProperty(origin, rpId, challenge, null);

            AuthenticationRequest authenticationRequest = new AuthenticationRequest(
                    credentialId,
                    userHandle,
                    authenticatorData,
                    clientDataJSON,
                    signature,
                    null
            );

            AuthenticationParameters authenticationParameters = new AuthenticationParameters(
                    serverProperty,
                    authenticator,
                    false,
                    true
            );

            AuthenticationData authenticationData = webAuthnManager.parse(authenticationRequest);
            webAuthnManager.validate(authenticationData, authenticationParameters);

            if (!authenticationData.getAuthenticatorData().isFlagUP()
                    || !authenticationData.getAuthenticatorData().isFlagUV()) {
                log.warn("Passkey authentication failed: user verification not performed");
                return null;
            }

            authFactor.setSignCount(authenticationData.getAuthenticatorData().getSignCount());
            authFactor.setLastUsedAt(java.time.LocalDateTime.now());
            authFactorRepository.save(authFactor);

            removePasskeyChallenge(sessionId);
            log.info("Passkey authentication successful for user: {}", user.getUsername());

            return user;

        } catch (ValidationException e) {
            log.error("Passkey authentication validation failed", e);
            return null;
        } catch (Exception e) {
            log.error("Passkey authentication error", e);
            return null;
        }
    }

    private void storePasskeyChallenge(String sessionId, Challenge challenge) {
        String key = PASSKEY_CHALLENGE_KEY_PREFIX + sessionId;
        redisTemplate.opsForValue().set(key, challenge.getValue(), CHALLENGE_EXPIRE_MINUTES, TimeUnit.MINUTES);
    }

    private Challenge getStoredPasskeyChallenge(String sessionId) {
        String key = PASSKEY_CHALLENGE_KEY_PREFIX + sessionId;
        byte[] value = (byte[]) redisTemplate.opsForValue().get(key);
        if (value == null) {
            return null;
        }
        return new DefaultChallenge(value);
    }

    private void removePasskeyChallenge(String sessionId) {
        String key = PASSKEY_CHALLENGE_KEY_PREFIX + sessionId;
        redisTemplate.delete(key);
    }
}

package com.mfa.service;

import com.mfa.dto.WebAuthnAssertion;
import com.mfa.dto.WebAuthnCredential;
import com.mfa.dto.WebAuthnOptionsResponse;
import com.mfa.entity.User;

public interface WebAuthnService {

    WebAuthnOptionsResponse generateRegistrationOptions(String sessionId, User user);

    boolean verifyRegistration(String sessionId, WebAuthnCredential credential, User user);

    WebAuthnOptionsResponse generateAuthenticationOptions(String sessionId, User user);

    boolean verifyAuthentication(String sessionId, WebAuthnAssertion assertion, User user);

    WebAuthnOptionsResponse generatePasskeyAuthenticationOptions(String sessionId);

    User verifyPasskeyAuthentication(String sessionId, WebAuthnAssertion assertion);

    WebAuthnOptionsResponse generatePasskeyRegistrationOptions(String sessionId, User user);
}

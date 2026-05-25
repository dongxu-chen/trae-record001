package com.mfa.dto;

import com.webauthn4j.data.PublicKeyCredentialCreationOptions;
import com.webauthn4j.data.PublicKeyCredentialRequestOptions;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WebAuthnOptionsResponse {

    private String challenge;
    private PublicKeyCredentialCreationOptions registrationOptions;
    private PublicKeyCredentialRequestOptions authenticationOptions;
}

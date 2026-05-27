package com.sso.auth;

import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;

import java.util.Collection;

public class MfaAuthenticationToken extends UsernamePasswordAuthenticationToken {

    private final String mfaCode;

    public MfaAuthenticationToken(Object principal, Object credentials, String mfaCode) {
        super(principal, credentials);
        this.mfaCode = mfaCode;
    }

    public MfaAuthenticationToken(Object principal, Object credentials, String mfaCode,
                                  Collection<? extends GrantedAuthority> authorities) {
        super(principal, credentials, authorities);
        this.mfaCode = mfaCode;
    }

    public String getMfaCode() {
        return mfaCode;
    }
}

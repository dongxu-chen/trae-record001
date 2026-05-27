package com.sso.auth;

import com.sso.entity.User;
import com.sso.repository.UserRepository;
import com.sso.service.CustomUserDetailsService;
import com.sso.service.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class MfaAuthenticationProviderTest {

    @Mock
    private UserService userService;

    @Mock
    private UserDetailsService userDetailsService;

    @Mock
    private PasswordEncoder passwordEncoder;

    @InjectMocks
    private MfaAuthenticationProvider mfaAuthenticationProvider;

    private User testUser;
    private UserDetails testUserDetails;

    @BeforeEach
    void setUp() {
        testUser = new User();
        testUser.setId(1L);
        testUser.setUsername("testuser");
        testUser.setEmail("test@example.com");
        testUser.setMfaEnabled(true);
        testUser.setMfaSecret("TESTSECRET123456");

        testUserDetails = org.springframework.security.core.userdetails.User
                .withUsername("testuser")
                .password("encodedPassword")
                .authorities("ROLE_USER")
                .build();
    }

    @Test
    void testSupportsMfaAuthenticationToken() {
        assertTrue(mfaAuthenticationProvider.supports(MfaAuthenticationToken.class));
    }

    @Test
    void testDoesNotSupportOtherAuthentication() {
        assertFalse(mfaAuthenticationProvider.supports(Authentication.class));
    }

    @Test
    void testGenerateMfaSecret() {
        String secret = mfaAuthenticationProvider.generateMfaSecret();
        assertNotNull(secret);
        assertTrue(secret.length() >= 16);
    }

    @Test
    void testGenerateQrCodeUri() {
        String secret = "TESTSECRET123456";
        String qrUri = mfaAuthenticationProvider.generateQrCodeUri(secret, "testuser", "SSO Test");

        assertNotNull(qrUri);
        assertTrue(qrUri.contains("otpauth://totp/"));
        assertTrue(qrUri.contains("testuser"));
        assertTrue(qrUri.contains("SSO%20Test"));
        assertTrue(qrUri.contains("TESTSECRET123456"));
    }

    @Test
    void testVerifyMfaCodeWithInvalidCode() {
        String secret = "TESTSECRET123456";
        String invalidCode = "000000";

        assertFalse(mfaAuthenticationProvider.verifyMfaCode(secret, invalidCode));
    }

    @Test
    void testAuthenticateWithNullMfaCodeWhenMfaEnabled() {
        MfaAuthenticationToken token = new MfaAuthenticationToken("testuser", "password", null);

        when(userDetailsService.loadUserByUsername("testuser")).thenReturn(testUserDetails);
        when(userService.findByUsername("testuser")).thenReturn(Optional.of(testUser));
        when(passwordEncoder.matches(anyString(), anyString())).thenReturn(true);

        assertThrows(BadCredentialsException.class, () -> mfaAuthenticationProvider.authenticate(token));
    }

    @Test
    void testAuthenticateWithInvalidPassword() {
        MfaAuthenticationToken token = new MfaAuthenticationToken("testuser", "wrongpassword", "123456");

        when(userDetailsService.loadUserByUsername("testuser")).thenReturn(testUserDetails);
        when(userService.findByUsername("testuser")).thenReturn(Optional.of(testUser));
        when(passwordEncoder.matches(anyString(), anyString())).thenReturn(false);

        assertThrows(BadCredentialsException.class, () -> mfaAuthenticationProvider.authenticate(token));
    }

    @Test
    void testAuthenticateWhenUserNotFound() {
        MfaAuthenticationToken token = new MfaAuthenticationToken("nonexistent", "password", "123456");

        when(userDetailsService.loadUserByUsername("nonexistent")).thenReturn(testUserDetails);
        when(userService.findByUsername("nonexistent")).thenReturn(Optional.empty());

        assertThrows(BadCredentialsException.class, () -> mfaAuthenticationProvider.authenticate(token));
    }
}

package com.sso.auth;

import com.sso.config.properties.SsoProperties;
import com.sso.entity.User;
import com.sso.service.UserService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Slf4j
@Component
public class MfaAuthenticationFilter extends UsernamePasswordAuthenticationFilter {

    private final UserService userService;
    private final SsoProperties ssoProperties;
    private final AuthenticationManager authenticationManager;

    public MfaAuthenticationFilter(UserService userService, SsoProperties ssoProperties, AuthenticationManager authenticationManager) {
        this.userService = userService;
        this.ssoProperties = ssoProperties;
        this.authenticationManager = authenticationManager;
        setAuthenticationManager(authenticationManager);
        setFilterProcessesUrl("/login");
    }

    @Override
    public Authentication attemptAuthentication(HttpServletRequest request, HttpServletResponse response)
            throws AuthenticationException {

        String username = obtainUsername(request);
        String password = obtainPassword(request);
        String mfaCode = request.getParameter("mfaCode");

        username = username != null ? username.trim() : "";
        password = password != null ? password : "";
        mfaCode = mfaCode != null ? mfaCode.trim() : "";

        log.debug("Attempting MFA authentication for user: {}", username);

        if (ssoProperties.getLogin().isMfaEnabled()) {
            User user = userService.findByUsername(username).orElse(null);
            if (user != null && user.isMfaEnabled()) {
                log.debug("MFA is enabled for user: {}, validating MFA code", username);
                MfaAuthenticationToken authRequest = new MfaAuthenticationToken(username, password, mfaCode);
                setDetails(request, authRequest);
                return authenticationManager.authenticate(authRequest);
            }
        }

        return super.attemptAuthentication(request, response);
    }

    @Override
    protected void successfulAuthentication(HttpServletRequest request, HttpServletResponse response,
                                            FilterChain chain, Authentication authResult)
            throws IOException, ServletException {
        super.successfulAuthentication(request, response, chain, authResult);
    }
}

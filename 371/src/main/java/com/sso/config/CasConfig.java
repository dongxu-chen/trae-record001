package com.sso.config;

import com.sso.config.properties.SsoProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.cas.ServiceProperties;
import org.springframework.security.cas.authentication.CasAuthenticationProvider;
import org.springframework.security.cas.web.CasAuthenticationEntryPoint;
import org.springframework.security.cas.web.CasAuthenticationFilter;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.security.web.authentication.AuthenticationFailureHandler;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;

@Slf4j
@Configuration
@ConditionalOnProperty(name = "sso.cas.server-url")
@RequiredArgsConstructor
public class CasConfig {

    private final SsoProperties ssoProperties;

    @Bean
    public ServiceProperties serviceProperties() {
        ServiceProperties serviceProperties = new ServiceProperties();
        serviceProperties.setService(ssoProperties.getCas().getServiceUrl() + "/login/cas");
        serviceProperties.setSendRenew(false);
        serviceProperties.setAuthenticateAllArtifacts(true);
        return serviceProperties;
    }

    @Bean
    public CasAuthenticationEntryPoint casAuthenticationEntryPoint() {
        CasAuthenticationEntryPoint entryPoint = new CasAuthenticationEntryPoint();
        entryPoint.setLoginUrl(ssoProperties.getCas().getServerUrl() + "/login");
        entryPoint.setServiceProperties(serviceProperties());
        return entryPoint;
    }

    @Bean
    public CasAuthenticationFilter casAuthenticationFilter(
            org.springframework.security.authentication.AuthenticationManager authenticationManager,
            @Qualifier("customAuthenticationSuccessHandler") AuthenticationSuccessHandler successHandler,
            AuthenticationFailureHandler failureHandler) {

        CasAuthenticationFilter filter = new CasAuthenticationFilter();
        filter.setFilterProcessesUrl("/login/cas");
        filter.setAuthenticationManager(authenticationManager);
        filter.setAuthenticationSuccessHandler(successHandler);
        filter.setAuthenticationFailureHandler(failureHandler);
        log.info("CAS authentication filter configured with server: {}", ssoProperties.getCas().getServerUrl());
        return filter;
    }

    @Bean
    public CasAuthenticationProvider casAuthenticationProvider(
            org.springframework.security.core.userdetails.UserDetailsService userDetailsService,
            org.springframework.security.crypto.password.PasswordEncoder passwordEncoder) {

        CasAuthenticationProvider provider = new CasAuthenticationProvider();
        provider.setServiceProperties(serviceProperties());
        provider.setTicketValidator(ticketValidator());
        provider.setUserDetailsService(userDetailsService);
        provider.setKey("cas-sso-key");
        return provider;
    }

    @Bean
    public org.apereo.cas.client.validation.TicketValidator ticketValidator() {
        String casServerUrlPrefix = ssoProperties.getCas().getServerUrl();
        return new org.apereo.cas.client.validation.Cas30ServiceTicketValidator(casServerUrlPrefix);
    }
}

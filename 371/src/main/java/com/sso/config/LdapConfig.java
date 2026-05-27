package com.sso.config;

import com.sso.config.properties.SsoProperties;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.ldap.core.AuthenticationSource;
import org.springframework.ldap.core.LdapTemplate;
import org.springframework.ldap.core.support.DefaultTlsDirContextAuthenticationStrategy;
import org.springframework.ldap.core.support.LdapContextSource;

@Configuration
@ConditionalOnProperty(name = "sso.ldap.enabled", havingValue = "true")
@RequiredArgsConstructor
public class LdapConfig {

    private final SsoProperties ssoProperties;

    @Bean
    public LdapContextSource ldapContextSource() {
        SsoProperties.LdapProperties ldapProps = ssoProperties.getLdap();
        LdapContextSource contextSource = new LdapContextSource();
        contextSource.setUrls(ldapProps.getUrls());
        contextSource.setBase(ldapProps.getBase());
        contextSource.setUserDn(ldapProps.getManagerDn());
        contextSource.setPassword(ldapProps.getManagerPassword());
        contextSource.setAuthenticationSource(new AuthenticationSource() {
            @Override
            public String getPrincipal() {
                return ldapProps.getManagerDn();
            }

            @Override
            public String getCredentials() {
                return ldapProps.getManagerPassword();
            }
        });
        contextSource.setAuthenticationStrategy(new DefaultTlsDirContextAuthenticationStrategy());
        contextSource.afterPropertiesSet();
        return contextSource;
    }

    @Bean
    public LdapTemplate ldapTemplate() {
        return new LdapTemplate(ldapContextSource());
    }
}

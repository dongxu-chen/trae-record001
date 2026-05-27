package com.sso.config;

import com.sso.auth.CustomAuthenticationSuccessHandler;
import com.sso.service.SocialLoginUserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Slf4j
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
@ConditionalOnProperty(name = "spring.security.oauth2.client.registration.google.client-id")
public class SocialLoginConfig {

    private final CustomAuthenticationSuccessHandler successHandler;
    private final SocialLoginUserService socialLoginUserService;

    @Bean
    @Order(3)
    public SecurityFilterChain socialLoginSecurityFilterChain(HttpSecurity http) throws Exception {
        http
                .securityMatcher("/login/oauth2/**", "/oauth2/authorization/**")
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/login/oauth2/**", "/oauth2/authorization/**").permitAll()
                        .anyRequest().authenticated()
                )
                .oauth2Login(oauth2 -> oauth2
                        .loginPage("/login")
                        .successHandler(successHandler)
                        .failureUrl("/login?error=social")
                        .userInfoEndpoint(userInfo -> userInfo
                                .oidcUserService(socialLoginUserService)
                        )
                );

        log.info("Social login security filter chain configured");
        return http.build();
    }
}

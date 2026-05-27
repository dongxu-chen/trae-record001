package com.sso.config;

import com.sso.config.properties.SsoProperties;
import com.sso.entity.OAuth2Client;
import com.sso.repository.OAuth2ClientRepository;
import com.sso.service.CustomUserDetailsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.authentication.AuthenticationProvider;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.core.AuthorizationGrantType;
import org.springframework.security.oauth2.core.ClientAuthenticationMethod;
import org.springframework.security.oauth2.core.oidc.OidcScopes;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.server.authorization.JdbcOAuth2AuthorizationConsentService;
import org.springframework.security.oauth2.server.authorization.JdbcOAuth2AuthorizationService;
import org.springframework.security.oauth2.server.authorization.OAuth2AuthorizationConsentService;
import org.springframework.security.oauth2.server.authorization.OAuth2AuthorizationService;
import org.springframework.security.oauth2.server.authorization.client.JdbcRegisteredClientRepository;
import org.springframework.security.oauth2.server.authorization.client.RegisteredClient;
import org.springframework.security.oauth2.server.authorization.client.RegisteredClientRepository;
import org.springframework.security.oauth2.server.authorization.config.annotation.web.configuration.OAuth2AuthorizationServerConfiguration;
import org.springframework.security.oauth2.server.authorization.config.annotation.web.configurers.OAuth2AuthorizationServerConfigurer;
import org.springframework.security.oauth2.server.authorization.settings.AuthorizationServerSettings;
import org.springframework.security.oauth2.server.authorization.settings.ClientSettings;
import org.springframework.security.oauth2.server.authorization.settings.OAuth2TokenFormat;
import org.springframework.security.oauth2.server.authorization.settings.TokenSettings;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.LoginUrlAuthenticationEntryPoint;

import java.security.KeyStore;
import java.time.Duration;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;

@Slf4j
@Configuration
@RequiredArgsConstructor
@Order(Ordered.HIGHEST_PRECEDENCE)
public class OAuth2AuthorizationServerConfig {

    private final SsoProperties ssoProperties;
    private final OAuth2ClientRepository clientRepository;
    private final CustomUserDetailsService userDetailsService;
    private final PasswordEncoder passwordEncoder;
    private final JdbcTemplate jdbcTemplate;

    @Bean
    @Order(1)
    public SecurityFilterChain authorizationServerSecurityFilterChain(HttpSecurity http) throws Exception {
        OAuth2AuthorizationServerConfiguration.applyDefaultSecurity(http);

        http.getConfigurer(OAuth2AuthorizationServerConfigurer.class)
                .oidc(Customizer.withDefaults())
                .authorizationEndpoint(auth -> auth
                        .consentPage("/oauth2/consent")
                )
                .clientAuthentication(client -> client
                        .authenticationProvider(customClientAuthenticationProvider())
                );

        http
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint(new LoginUrlAuthenticationEntryPoint("/login"))
                )
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()));

        return http.build();
    }

    @Bean
    public RegisteredClientRepository registeredClientRepository() {
        JdbcRegisteredClientRepository jdbcRepository = new JdbcRegisteredClientRepository(jdbcTemplate);

        initializeDefaultClients(jdbcRepository);

        return new CustomRegisteredClientRepository(jdbcRepository, clientRepository, this);
    }

    private void initializeDefaultClients(JdbcRegisteredClientRepository jdbcRepository) {
        List<OAuth2Client> clients = clientRepository.findAll();
        if (clients.isEmpty()) {
            OAuth2Client defaultClient = new OAuth2Client();
            defaultClient.setClientId("web-client");
            defaultClient.setClientName("Web Application Client");
            defaultClient.setClientSecret(passwordEncoder.encode("web-client-secret"));
            defaultClient.setRedirectUris(new HashSet<>(Arrays.asList(
                    "http://localhost:8081/login/oauth2/code/sso",
                    "https://app.example.com/login/oauth2/code/sso"
            )));
            defaultClient.setScopes(new HashSet<>(Arrays.asList(
                    OidcScopes.OPENID,
                    OidcScopes.PROFILE,
                    OidcScopes.EMAIL,
                    "read",
                    "write"
            )));
            defaultClient.setAuthorizedGrantTypes(new HashSet<>(Arrays.asList(
                    AuthorizationGrantType.AUTHORIZATION_CODE.getValue(),
                    AuthorizationGrantType.REFRESH_TOKEN.getValue(),
                    AuthorizationGrantType.CLIENT_CREDENTIALS.getValue(),
                    AuthorizationGrantType.PASSWORD.getValue()
            )));
            defaultClient.setClientAuthenticationMethods(new HashSet<>(Arrays.asList(
                    ClientAuthenticationMethod.CLIENT_SECRET_BASIC.getValue(),
                    ClientAuthenticationMethod.CLIENT_SECRET_POST.getValue()
            )));
            defaultClient.setAccessTokenTtl(Duration.ofHours(1));
            defaultClient.setRefreshTokenTtl(Duration.ofDays(30));
            defaultClient.setAuthorizationCodeTtl(Duration.ofMinutes(5));
            defaultClient.setRequireConsent(true);
            defaultClient.setRequirePkce(false);
            defaultClient.setEnabled(true);
            defaultClient.setDescription("Default web application client for testing");
            clientRepository.save(defaultClient);
            log.info("Created default OAuth2 client: web-client");

            OAuth2Client mobileClient = new OAuth2Client();
            mobileClient.setClientId("mobile-client");
            mobileClient.setClientName("Mobile Application Client");
            mobileClient.setClientSecret(passwordEncoder.encode("mobile-client-secret"));
            mobileClient.setRedirectUris(new HashSet<>(Arrays.asList(
                    "myapp://callback"
            )));
            mobileClient.setScopes(new HashSet<>(Arrays.asList(
                    OidcScopes.OPENID,
                    OidcScopes.PROFILE,
                    OidcScopes.EMAIL
            )));
            mobileClient.setAuthorizedGrantTypes(new HashSet<>(Arrays.asList(
                    AuthorizationGrantType.AUTHORIZATION_CODE.getValue(),
                    AuthorizationGrantType.REFRESH_TOKEN.getValue()
            )));
            mobileClient.setClientAuthenticationMethods(new HashSet<>(Arrays.asList(
                    ClientAuthenticationMethod.NONE.getValue()
            )));
            mobileClient.setAccessTokenTtl(Duration.ofHours(2));
            mobileClient.setRefreshTokenTtl(Duration.ofDays(90));
            mobileClient.setAuthorizationCodeTtl(Duration.ofMinutes(10));
            mobileClient.setRequireConsent(true);
            mobileClient.setRequirePkce(true);
            mobileClient.setEnabled(true);
            mobileClient.setDescription("Mobile application client with PKCE");
            clientRepository.save(mobileClient);
            log.info("Created default OAuth2 client: mobile-client");
        }
    }

    public RegisteredClient toRegisteredClient(OAuth2Client client) {
        TokenSettings tokenSettings = TokenSettings.builder()
                .accessTokenFormat(OAuth2TokenFormat.SELF_CONTAINED)
                .accessTokenTimeToLive(client.getAccessTokenTtl())
                .refreshTokenTimeToLive(client.getRefreshTokenTtl())
                .authorizationCodeTimeToLive(client.getAuthorizationCodeTtl())
                .reuseRefreshTokens(true)
                .build();

        ClientSettings clientSettings = ClientSettings.builder()
                .requireAuthorizationConsent(client.isRequireConsent())
                .requireProofKey(client.isRequirePkce())
                .build();

        RegisteredClient.Builder builder = RegisteredClient.withId(client.getClientId())
                .clientId(client.getClientId())
                .clientName(client.getClientName())
                .clientSecret(client.getClientSecret());

        for (String method : client.getClientAuthenticationMethods()) {
            builder.clientAuthenticationMethod(new ClientAuthenticationMethod(method));
        }

        for (String grantType : client.getAuthorizedGrantTypes()) {
            builder.authorizationGrantType(new AuthorizationGrantType(grantType));
        }

        for (String redirectUri : client.getRedirectUris()) {
            builder.redirectUri(redirectUri);
        }

        for (String scope : client.getScopes()) {
            builder.scope(scope);
        }

        return builder
                .tokenSettings(tokenSettings)
                .clientSettings(clientSettings)
                .build();
    }

    @Bean
    public OAuth2AuthorizationService authorizationService() {
        return new JdbcOAuth2AuthorizationService(jdbcTemplate, registeredClientRepository());
    }

    @Bean
    public OAuth2AuthorizationConsentService authorizationConsentService() {
        return new JdbcOAuth2AuthorizationConsentService(jdbcTemplate, registeredClientRepository());
    }

    @Bean
    public AuthorizationServerSettings authorizationServerSettings() {
        return AuthorizationServerSettings.builder()
                .issuer(ssoProperties.getOauth2().getIssuer())
                .authorizationEndpoint("/oauth2/authorize")
                .tokenEndpoint("/oauth2/token")
                .tokenIntrospectionEndpoint("/oauth2/introspect")
                .tokenRevocationEndpoint("/oauth2/revoke")
                .jwkSetEndpoint("/oauth2/jwks")
                .oidcUserInfoEndpoint("/oauth2/userinfo")
                .oidcClientRegistrationEndpoint("/oauth2/register")
                .build();
    }

    @Bean
    @Primary
    public JwtDecoder jwtDecoder() throws Exception {
        SsoProperties.OAuth2Properties oauth2Props = ssoProperties.getOauth2();
        return NimbusJwtDecoder.withJwkSetUri(oauth2Props.getIssuer() + "/oauth2/jwks").build();
    }

    private AuthenticationProvider customClientAuthenticationProvider() {
        return new AuthenticationProvider() {
            @Override
            public org.springframework.security.core.Authentication authenticate(
                    org.springframework.security.core.Authentication authentication)
                    throws org.springframework.security.core.AuthenticationException {
                log.debug("Custom client authentication for: {}", authentication.getName());
                return authentication;
            }

            @Override
            public boolean supports(Class<?> authentication) {
                return true;
            }
        };
    }
}

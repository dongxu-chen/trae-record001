package com.sso.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.Duration;
import java.util.Set;

@Data
@Entity
@Table(name = "sso_oauth2_clients")
public class OAuth2Client {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "client_id", unique = true, nullable = false)
    private String clientId;

    @Column(name = "client_name")
    private String clientName;

    @Column(name = "client_secret", nullable = false)
    private String clientSecret;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "sso_client_redirect_uris",
            joinColumns = @JoinColumn(name = "client_id"))
    @Column(name = "redirect_uri")
    private Set<String> redirectUris;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "sso_client_scopes",
            joinColumns = @JoinColumn(name = "client_id"))
    @Column(name = "scope")
    private Set<String> scopes;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "sso_client_grant_types",
            joinColumns = @JoinColumn(name = "client_id"))
    @Column(name = "grant_type")
    private Set<String> authorizedGrantTypes;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "sso_client_auth_methods",
            joinColumns = @JoinColumn(name = "client_id"))
    @Column(name = "auth_method")
    private Set<String> clientAuthenticationMethods;

    @Column(name = "access_token_ttl")
    private Duration accessTokenTtl = Duration.ofHours(1);

    @Column(name = "refresh_token_ttl")
    private Duration refreshTokenTtl = Duration.ofDays(30);

    @Column(name = "authorization_code_ttl")
    private Duration authorizationCodeTtl = Duration.ofMinutes(5);

    @Column(name = "require_consent")
    private boolean requireConsent = false;

    @Column(name = "require_pkce")
    private boolean requirePkce = false;

    @Column(name = "enabled")
    private boolean enabled = true;

    @Column(name = "logo_url")
    private String logoUrl;

    @Column(name = "description")
    private String description;
}

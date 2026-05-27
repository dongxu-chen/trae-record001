package com.sso.entity;

import jakarta.persistence.*;
import lombok.Data;

@Data
@Entity
@Table(name = "sso_saml2_sp")
public class Saml2Sp {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "entity_id", unique = true, nullable = false)
    private String entityId;

    @Column(name = "sp_name")
    private String spName;

    @Column(name = "metadata_url")
    private String metadataUrl;

    @Column(name = "assertion_consumer_service_url", nullable = false)
    private String assertionConsumerServiceUrl;

    @Column(name = "single_logout_service_url")
    private String singleLogoutServiceUrl;

    @Column(name = "certificate", columnDefinition = "TEXT")
    private String certificate;

    @Column(name = "name_id_format")
    private String nameIdFormat = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified";

    @Column(name = "sign_authn_requests")
    private boolean signAuthnRequests = false;

    @Column(name = "encrypt_assertions")
    private boolean encryptAssertions = false;

    @Column(name = "enabled")
    private boolean enabled = true;

    @Column(name = "description")
    private String description;

    @Column(name = "logo_url")
    private String logoUrl;
}

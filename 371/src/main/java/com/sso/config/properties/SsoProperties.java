package com.sso.config.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "sso")
public class SsoProperties {

    private LoginProperties login = new LoginProperties();
    private LdapProperties ldap = new LdapProperties();
    private Saml2Properties saml2 = new Saml2Properties();
    private OAuth2Properties oauth2 = new OAuth2Properties();
    private CasProperties cas = new CasProperties();
    private SyncProperties sync = new SyncProperties();

    @Data
    public static class LoginProperties {
        private String title = "统一身份认证";
        private String logo = "/images/logo.png";
        private String backgroundImage = "/images/login-bg.jpg";
        private boolean showCopyright = true;
        private String copyrightText = "© 2024 SSO Center";
        private boolean enableRememberMe = true;
        private boolean mfaEnabled = true;
        private boolean mfaRequired = false;
    }

    @Data
    public static class LdapProperties {
        private boolean enabled = false;
        private String[] urls;
        private String base;
        private String userDnPattern;
        private String groupSearchBase;
        private String groupSearchFilter = "member={0}";
        private String managerDn;
        private String managerPassword;
    }

    @Data
    public static class Saml2Properties {
        private String entityId;
        private String baseUrl;
        private String signingKeyLocation;
        private String signingCertLocation;
        private String encryptionKeyLocation;
        private String encryptionCertLocation;
    }

    @Data
    public static class OAuth2Properties {
        private String issuer;
        private String jksKeystore;
        private String jksPassword;
        private String keyAlias;
        private String keyPassword;
    }

    @Data
    public static class CasProperties {
        private String serverUrl;
        private String serviceUrl;
    }

    @Data
    public static class SyncProperties {
        private String ldapSyncCron = "0 0 2 * * ?";
        private boolean syncOnStartup = false;
    }
}

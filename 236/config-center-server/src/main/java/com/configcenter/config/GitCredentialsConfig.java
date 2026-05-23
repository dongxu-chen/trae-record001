package com.configcenter.config;

import com.configcenter.util.AesEncryptor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.config.server.environment.JGitEnvironmentRepository;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

@Configuration
public class GitCredentialsConfig {

    @Value("${config.git.username-encrypted:}")
    private String usernameEncrypted;

    @Value("${config.git.password-encrypted:}")
    private String passwordEncrypted;

    @Value("${CONFIG_ENCRYPT_KEY:}")
    private String encryptKey;

    private final Environment environment;

    public GitCredentialsConfig(Environment environment) {
        this.environment = environment;
    }

    @Bean
    public JGitEnvironmentRepository gitEnvironmentRepository(
            org.springframework.cloud.config.server.environment.MultipleJGitEnvironmentProperties properties) {

        String actualEncryptKey = environment.getProperty("CONFIG_ENCRYPT_KEY", "");

        String username = decryptCredential(usernameEncrypted, actualEncryptKey);
        String password = decryptCredential(passwordEncrypted, actualEncryptKey);

        if (username != null && !username.isEmpty()) {
            properties.setUsername(username);
        }
        if (password != null && !password.isEmpty()) {
            properties.setPassword(password);
        }

        return new JGitEnvironmentRepository(properties);
    }

    private String decryptCredential(String encrypted, String encryptKey) {
        if (encrypted == null || encrypted.isEmpty()) {
            return null;
        }
        if (encryptKey == null || encryptKey.isEmpty()) {
            throw new IllegalStateException("CONFIG_ENCRYPT_KEY 环境变量未设置，无法解密Git凭证");
        }
        try {
            AesEncryptor encryptor = new AesEncryptor(encryptKey);
            return encryptor.decrypt(encrypted);
        } catch (Exception e) {
            throw new IllegalStateException("Git凭证解密失败，请检查CONFIG_ENCRYPT_KEY是否正确", e);
        }
    }
}

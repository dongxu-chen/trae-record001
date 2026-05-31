package com.depguard.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.kohsuke.github.GitHub;
import org.kohsuke.github.GitHubBuilder;

import java.io.IOException;

@Configuration
public class GitHubConfig {

    @Value("${depguard.github.token:}")
    private String githubToken;

    @Bean
    public GitHub gitHub() throws IOException {
        if (githubToken != null && !githubToken.isBlank()) {
            return new GitHubBuilder().withOAuthToken(githubToken).build();
        }
        return GitHub.connectAnonymously();
    }
}

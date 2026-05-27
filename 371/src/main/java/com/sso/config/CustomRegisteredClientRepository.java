package com.sso.config;

import com.sso.entity.OAuth2Client;
import com.sso.repository.OAuth2ClientRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.oauth2.server.authorization.client.RegisteredClient;
import org.springframework.security.oauth2.server.authorization.client.RegisteredClientRepository;

@Slf4j
@RequiredArgsConstructor
public class CustomRegisteredClientRepository implements RegisteredClientRepository {

    private final RegisteredClientRepository jdbcRepository;
    private final OAuth2ClientRepository clientRepository;
    private final OAuth2AuthorizationServerConfig config;

    @Override
    public void save(RegisteredClient registeredClient) {
        jdbcRepository.save(registeredClient);
    }

    @Override
    public RegisteredClient findById(String id) {
        return jdbcRepository.findById(id);
    }

    @Override
    public RegisteredClient findByClientId(String clientId) {
        OAuth2Client client = clientRepository.findByClientId(clientId).orElse(null);
        if (client != null && client.isEnabled()) {
            log.debug("Found custom OAuth2 client: {}", clientId);
            return config.toRegisteredClient(client);
        }
        log.debug("Using JDBC OAuth2 client: {}", clientId);
        return jdbcRepository.findByClientId(clientId);
    }
}

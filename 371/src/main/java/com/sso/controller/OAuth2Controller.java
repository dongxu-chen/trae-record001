package com.sso.controller;

import com.sso.entity.OAuth2Client;
import com.sso.repository.OAuth2ClientRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.core.oidc.OidcUserInfo;
import org.springframework.security.oauth2.server.authorization.OAuth2Authorization;
import org.springframework.security.oauth2.server.authorization.OAuth2AuthorizationService;
import org.springframework.security.oauth2.server.authorization.client.RegisteredClient;
import org.springframework.security.oauth2.server.authorization.client.RegisteredClientRepository;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.security.Principal;
import java.util.Map;

@Slf4j
@Controller
@RequiredArgsConstructor
public class OAuth2Controller {

    private final RegisteredClientRepository registeredClientRepository;
    private final OAuth2ClientRepository clientRepository;
    private final OAuth2AuthorizationService authorizationService;

    @GetMapping("/oauth2/consent")
    public String consent(
            Authentication authentication,
            @RequestParam("client_id") String clientId,
            @RequestParam("scope") String scope,
            @RequestParam("state") String state,
            @RequestParam("user_code") String userCode,
            Model model) {

        RegisteredClient registeredClient = registeredClientRepository.findByClientId(clientId);
        OAuth2Client client = clientRepository.findByClientId(clientId).orElse(null);

        model.addAttribute("clientId", clientId);
        model.addAttribute("clientName", client != null ? client.getClientName() : registeredClient.getClientName());
        model.addAttribute("clientLogo", client != null ? client.getLogoUrl() : null);
        model.addAttribute("scopes", scope.split(" "));
        model.addAttribute("state", state);
        model.addAttribute("principalName", authentication.getName());

        return "oauth2-consent";
    }

    @GetMapping("/oauth2/userinfo")
    public OidcUserInfo userInfo(Principal principal) {
        String username = principal.getName();
        return OidcUserInfo.builder()
                .subject(username)
                .name(username)
                .preferredUsername(username)
                .email(username + "@example.com")
                .claim("email_verified", true)
                .build();
    }
}

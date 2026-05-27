package com.sso.controller;

import com.sso.config.properties.SsoProperties;
import com.sso.entity.User;
import com.sso.service.UserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.security.Principal;

@Slf4j
@Controller
@RequiredArgsConstructor
public class LoginController {

    private final SsoProperties ssoProperties;
    private final UserService userService;

    @GetMapping("/login")
    public String login(@RequestParam(required = false) String error,
                        @RequestParam(required = false) String logout,
                        @RequestParam(required = false) String expired,
                        @RequestParam(required = false) String redirect_uri,
                        @RequestParam(required = false) String client_id,
                        @RequestParam(required = false) String protocol,
                        Model model) {

        model.addAttribute("loginConfig", ssoProperties.getLogin());
        model.addAttribute("redirectUri", redirect_uri);
        model.addAttribute("clientId", client_id);
        model.addAttribute("protocol", protocol);

        if (error != null) {
            model.addAttribute("error", error);
        }
        if (logout != null) {
            model.addAttribute("message", "You have been logged out successfully.");
        }
        if (expired != null) {
            model.addAttribute("error", "Your session has expired. Please log in again.");
        }

        return "login";
    }

    @GetMapping("/dashboard")
    public String dashboard(Authentication authentication, Model model) {
        if (authentication != null && authentication.isAuthenticated()) {
            String username = authentication.getName();
            User user = userService.findByUsername(username).orElse(null);
            model.addAttribute("user", user);
            model.addAttribute("username", username);
            model.addAttribute("authorities", authentication.getAuthorities());
        }
        return "dashboard";
    }

    @GetMapping("/logout-success")
    public String logoutSuccess() {
        return "logout-success";
    }
}

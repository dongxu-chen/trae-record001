package com.mfa.service;

import com.mfa.entity.User;

public interface JwtService {

    String generateToken(User user);

    String extractUsername(String token);

    boolean validateToken(String token, User user);
}

package com.sso.auth;

import com.sso.entity.User;
import com.sso.repository.UserRepository;
import com.sso.service.UserService;
import dev.samstevens.totp.code.CodeVerifier;
import dev.samstevens.totp.code.DefaultCodeGenerator;
import dev.samstevens.totp.code.DefaultCodeVerifier;
import dev.samstevens.totp.code.HashingAlgorithm;
import dev.samstevens.totp.qr.QrData;
import dev.samstevens.totp.qr.QrGenerator;
import dev.samstevens.totp.qr.ZxingPngQrGenerator;
import dev.samstevens.totp.secret.DefaultSecretGenerator;
import dev.samstevens.totp.secret.SecretGenerator;
import dev.samstevens.totp.time.SystemTimeProvider;
import dev.samstevens.totp.time.TimeProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.AuthenticationProvider;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.security.SecureRandom;
import java.util.HashSet;
import java.util.Set;

@Slf4j
@Component
@RequiredArgsConstructor
public class MfaAuthenticationProvider implements AuthenticationProvider {

    private static final int BACKUP_CODE_LENGTH = 8;
    private static final int BACKUP_CODE_COUNT = 10;
    private static final String BACKUP_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

    private final UserService userService;
    private final UserDetailsService userDetailsService;
    private final PasswordEncoder passwordEncoder;
    private final UserRepository userRepository;

    @Override
    public Authentication authenticate(Authentication authentication) throws AuthenticationException {
        if (!(authentication instanceof MfaAuthenticationToken mfaToken)) {
            return null;
        }

        String username = mfaToken.getName();
        String password = mfaToken.getCredentials().toString();
        String mfaCode = mfaToken.getMfaCode();

        log.debug("MFA authentication attempt for user: {}", username);

        UserDetails userDetails = userDetailsService.loadUserByUsername(username);
        User user = userService.findByUsername(username)
                .orElseThrow(() -> new BadCredentialsException("Invalid username or password"));

        if (!passwordEncoder.matches(password, userDetails.getPassword())) {
            throw new BadCredentialsException("Invalid username or password");
        }

        if (user.isMfaEnabled()) {
            if (mfaCode == null || mfaCode.isEmpty()) {
                throw new BadCredentialsException("MFA code is required");
            }

            boolean isBackupCode = mfaCode.length() == BACKUP_CODE_LENGTH;
            
            if (isBackupCode) {
                if (!verifyBackupCode(user, mfaCode)) {
                    throw new BadCredentialsException("Invalid or used backup code");
                }
                log.info("Backup code used for user: {}", username);
            } else {
                if (!verifyMfaCode(user.getMfaSecret(), mfaCode)) {
                    throw new BadCredentialsException("Invalid MFA code");
                }
                log.debug("MFA code verified successfully for user: {}", username);
            }
        }

        return new UsernamePasswordAuthenticationToken(
                userDetails,
                password,
                userDetails.getAuthorities()
        );
    }

    @Override
    public boolean supports(Class<?> authentication) {
        return MfaAuthenticationToken.class.isAssignableFrom(authentication);
    }

    public boolean verifyMfaCode(String secret, String code) {
        TimeProvider timeProvider = new SystemTimeProvider();
        DefaultCodeGenerator codeGenerator = new DefaultCodeGenerator(HashingAlgorithm.SHA1, 6);
        CodeVerifier verifier = new DefaultCodeVerifier(codeGenerator, timeProvider);
        return verifier.isValidCode(secret, code);
    }

    public boolean verifyBackupCode(User user, String code) {
        Set<String> backupCodes = user.getMfaBackupCodes();
        Set<String> usedCodes = user.getUsedMfaBackupCodes();

        if (backupCodes == null || !backupCodes.contains(code)) {
            return false;
        }

        if (usedCodes != null && usedCodes.contains(code)) {
            log.warn("Attempt to use already consumed backup code for user: {}", user.getUsername());
            return false;
        }

        if (usedCodes == null) {
            usedCodes = new HashSet<>();
        }
        usedCodes.add(code);
        user.setUsedMfaBackupCodes(usedCodes);
        userRepository.save(user);

        log.info("Backup code consumed for user: {}, remaining: {}", 
                user.getUsername(), backupCodes.size() - usedCodes.size());
        return true;
    }

    public Set<String> generateBackupCodes() {
        SecureRandom random = new SecureRandom();
        Set<String> codes = new HashSet<>();

        while (codes.size() < BACKUP_CODE_COUNT) {
            StringBuilder code = new StringBuilder();
            for (int i = 0; i < BACKUP_CODE_LENGTH; i++) {
                code.append(BACKUP_CODE_CHARS.charAt(random.nextInt(BACKUP_CODE_CHARS.length())));
            }
            codes.add(code.toString());
        }

        return codes;
    }

    public Set<String> regenerateBackupCodes(User user) {
        Set<String> newCodes = generateBackupCodes();
        user.setMfaBackupCodes(newCodes);
        user.setUsedMfaBackupCodes(new HashSet<>());
        userRepository.save(user);

        log.info("Backup codes regenerated for user: {}", user.getUsername());
        return newCodes;
    }

    public int getRemainingBackupCodes(User user) {
        Set<String> backupCodes = user.getMfaBackupCodes();
        Set<String> usedCodes = user.getUsedMfaBackupCodes();

        if (backupCodes == null) {
            return 0;
        }

        int total = backupCodes.size();
        int used = usedCodes != null ? usedCodes.size() : 0;

        return total - used;
    }

    public String generateMfaSecret() {
        SecretGenerator secretGenerator = new DefaultSecretGenerator();
        return secretGenerator.generate();
    }

    public String generateQrCodeUri(String secret, String username, String issuer) {
        QrData data = new QrData.Builder()
                .label(username)
                .secret(secret)
                .issuer(issuer)
                .algorithm(HashingAlgorithm.SHA1)
                .digits(6)
                .period(30)
                .build();

        QrGenerator generator = new ZxingPngQrGenerator();
        return data.getUri();
    }
}

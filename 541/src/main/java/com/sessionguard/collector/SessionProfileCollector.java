package com.sessionguard.collector;

import com.sessionguard.model.IpContext;
import com.sessionguard.model.SessionProfile;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class SessionProfileCollector {

    private final IpContextCollector ipContextCollector;
    private final DeviceFingerprintCollector deviceFingerprintCollector;

    public SessionProfile collectNewSession(HttpServletRequest request, String userId) {
        IpContext ipContext = ipContextCollector.collect(request);

        return SessionProfile.builder()
                .sessionId(UUID.randomUUID().toString())
                .userId(userId)
                .cookieId(extractCookieId(request))
                .ipContext(ipContext)
                .deviceFingerprint(deviceFingerprintCollector.collect(request))
                .createdAt(LocalDateTime.now())
                .lastAccessedAt(LocalDateTime.now())
                .lastVerifiedAt(LocalDateTime.now())
                .lastActiveRegion(ipContext.getGeoCountry())
                .accessCount(1)
                .active(true)
                .invalidated(false)
                .build();
    }

    public SessionProfile updateFromRequest(SessionProfile existing, HttpServletRequest request) {
        IpContext newIp = ipContextCollector.collect(request);

        existing.setIpContext(newIp);
        existing.setDeviceFingerprint(deviceFingerprintCollector.collect(request));
        existing.setLastAccessedAt(LocalDateTime.now());
        existing.setLastVerifiedAt(LocalDateTime.now());
        existing.setAccessCount(existing.getAccessCount() + 1);

        if (!"UNKNOWN".equals(newIp.getGeoCountry())) {
            existing.setLastActiveRegion(newIp.getGeoCountry());
        }

        return existing;
    }

    private String extractCookieId(HttpServletRequest request) {
        if (request.getCookies() != null) {
            for (jakarta.servlet.http.Cookie cookie : request.getCookies()) {
                if ("JSESSIONID".equals(cookie.getName()) || "SESSION".equals(cookie.getName())) {
                    return cookie.getValue();
                }
            }
        }
        return UUID.randomUUID().toString();
    }
}

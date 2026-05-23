package com.shortlink.controller;

import com.shortlink.service.AccessLogService;
import com.shortlink.service.ShortLinkService;
import com.shortlink.util.Base62Encoder;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

import java.io.IOException;

@Slf4j
@Controller
@RequiredArgsConstructor
public class RedirectController {

    private final ShortLinkService shortLinkService;
    private final AccessLogService accessLogService;
    private final Base62Encoder base62Encoder;

    @GetMapping("/{shortCode}")
    public void redirect(@PathVariable String shortCode,
                         HttpServletRequest request,
                         HttpServletResponse response) throws IOException {
        try {
            String originUrl = shortLinkService.getOriginUrl(shortCode);

            shortLinkService.incrementPv(shortCode);

            String clientIp = getClientIp(request);
            String userAgent = request.getHeader("User-Agent");
            String fingerprint = base62Encoder.generateFingerprint(clientIp, userAgent);

            if (shortLinkService.isFirstVisitByFingerprint(shortCode, fingerprint)) {
                shortLinkService.incrementUv(shortCode);
            }

            accessLogService.logAccess(shortCode, request);

            response.sendRedirect(originUrl);
        } catch (Exception e) {
            log.warn("重定向失败: shortCode={}, error={}", shortCode, e.getMessage());
            response.setStatus(HttpServletResponse.SC_NOT_FOUND);
            response.getWriter().write("短链接不存在或已过期");
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_CLIENT_IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_X_FORWARDED_FOR");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip;
    }
}

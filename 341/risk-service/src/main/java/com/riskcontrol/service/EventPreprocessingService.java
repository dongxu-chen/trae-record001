package com.riskcontrol.service;

import com.riskcontrol.common.model.DeviceFingerprint;
import com.riskcontrol.common.model.RiskEvent;
import com.riskcontrol.common.utils.DeviceFingerprintUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class EventPreprocessingService {

    private static final Logger logger = LoggerFactory.getLogger(EventPreprocessingService.class);

    public void preprocessEvent(RiskEvent event) {
        preprocessIpAddress(event);
        preprocessDeviceFingerprint(event);
        preprocessUserAgent(event);
        preprocessEmail(event);
        preprocessPhone(event);
    }

    private void preprocessIpAddress(RiskEvent event) {
        String ipAddress = event.getIpAddress();
        if (ipAddress != null) {
            ipAddress = ipAddress.trim();
            if (ipAddress.contains(",")) {
                ipAddress = ipAddress.split(",")[0].trim();
            }
            event.setIpAddress(ipAddress);
            logger.debug("Preprocessed IP address: {}", ipAddress);
        }
    }

    private void preprocessDeviceFingerprint(RiskEvent event) {
        DeviceFingerprint fingerprint = event.getDeviceFingerprint();
        if (fingerprint == null) {
            return;
        }

        if (fingerprint.getUserAgent() != null) {
            fingerprint.setUserAgent(fingerprint.getUserAgent().trim());
        }

        if (fingerprint.getDeviceId() == null || fingerprint.getDeviceId().isEmpty()) {
            try {
                String deviceId = DeviceFingerprintUtil.generateDeviceId(fingerprint);
                fingerprint.setDeviceId(deviceId);
                logger.debug("Generated device ID: {}", deviceId);
            } catch (Exception e) {
                logger.warn("Failed to generate device ID", e);
            }
        }

        if (fingerprint.getIpAddress() == null && event.getIpAddress() != null) {
            fingerprint.setIpAddress(event.getIpAddress());
        }

        Map<String, String> attributes = fingerprint.getAdditionalAttributes();
        if (attributes != null && !attributes.isEmpty()) {
            String canvas = attributes.get("canvas");
            if (canvas != null && fingerprint.getCanvasFingerprint() == null) {
                fingerprint.setCanvasFingerprint(canvas);
            }
            String webgl = attributes.get("webgl");
            if (webgl != null && fingerprint.getWebglFingerprint() == null) {
                fingerprint.setWebglFingerprint(webgl);
            }
            String fonts = attributes.get("fonts");
            if (fonts != null && fingerprint.getFontsFingerprint() == null) {
                fingerprint.setFontsFingerprint(fonts);
            }
        }
    }

    private void preprocessUserAgent(RiskEvent event) {
        String userAgent = event.getUserAgent();
        if (userAgent != null) {
            userAgent = userAgent.trim();
            event.setUserAgent(userAgent);

            if (event.getDeviceFingerprint() != null &&
                    event.getDeviceFingerprint().getUserAgent() == null) {
                event.getDeviceFingerprint().setUserAgent(userAgent);
            }

            parseUserAgentDetails(event, userAgent);
        }
    }

    private void parseUserAgentDetails(RiskEvent event, String userAgent) {
        DeviceFingerprint fingerprint = event.getDeviceFingerprint();
        if (fingerprint == null) {
            return;
        }

        if (userAgent.contains("Windows")) {
            fingerprint.setOs("Windows");
        } else if (userAgent.contains("Mac OS X")) {
            fingerprint.setOs("macOS");
        } else if (userAgent.contains("Linux")) {
            fingerprint.setOs("Linux");
        } else if (userAgent.contains("Android")) {
            fingerprint.setOs("Android");
        } else if (userAgent.contains("iOS") || userAgent.contains("iPhone") || userAgent.contains("iPad")) {
            fingerprint.setOs("iOS");
        }

        if (userAgent.contains("Chrome") && !userAgent.contains("Edg")) {
            fingerprint.setBrowser("Chrome");
        } else if (userAgent.contains("Firefox")) {
            fingerprint.setBrowser("Firefox");
        } else if (userAgent.contains("Safari") && !userAgent.contains("Chrome")) {
            fingerprint.setBrowser("Safari");
        } else if (userAgent.contains("Edg")) {
            fingerprint.setBrowser("Edge");
        }

        if (userAgent.contains("Mobile")) {
            fingerprint.setPlatform("Mobile");
        } else if (userAgent.contains("Tablet") || userAgent.contains("iPad")) {
            fingerprint.setPlatform("Tablet");
        } else {
            fingerprint.setPlatform("Desktop");
        }
    }

    private void preprocessEmail(RiskEvent event) {
        String email = event.getEmail();
        if (email != null) {
            email = email.trim().toLowerCase();
            event.setEmail(email);
        }
    }

    private void preprocessPhone(RiskEvent event) {
        String phone = event.getPhone();
        if (phone != null) {
            phone = phone.replaceAll("\\D", "");
            if (!phone.startsWith("+")) {
                if (phone.length() == 11 && phone.startsWith("1")) {
                    phone = "+86" + phone;
                } else if (phone.length() == 10) {
                    phone = "+1" + phone;
                }
            }
            event.setPhone(phone);
        }
    }
}

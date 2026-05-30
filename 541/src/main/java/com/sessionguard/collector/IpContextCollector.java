package com.sessionguard.collector;

import com.sessionguard.model.IpContext;
import jakarta.servlet.http.HttpServletRequest;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

@Component
public class IpContextCollector {

    private static final String[] IP_HEADER_CANDIDATES = {
            "X-Forwarded-For",
            "Proxy-Client-IP",
            "WL-Proxy-Client-IP",
            "HTTP_X_FORWARDED_FOR",
            "HTTP_X_FORWARDED",
            "HTTP_X_CLUSTER_CLIENT_IP",
            "HTTP_CLIENT_IP",
            "HTTP_FORWARDED_FOR",
            "HTTP_FORWARDED",
            "HTTP_VIA",
            "REMOTE_ADDR"
    };

    public IpContext collect(HttpServletRequest request) {
        String ipAddress = resolveIpAddress(request);
        String subnetPrefix = extractSubnetPrefix(ipAddress, 24);

        return IpContext.builder()
                .ipAddress(ipAddress)
                .subnetPrefix(subnetPrefix)
                .geoCountry(resolveGeoCountry(ipAddress))
                .geoCity(resolveGeoCity(ipAddress))
                .geoRegion(resolveGeoRegion(ipAddress))
                .isp(resolveIsp(ipAddress))
                .isProxy(checkProxy(ipAddress))
                .isVpn(checkVpn(ipAddress))
                .isTor(checkTor(ipAddress))
                .isDataCenter(checkDataCenter(ipAddress))
                .build();
    }

    private String resolveIpAddress(HttpServletRequest request) {
        for (String header : IP_HEADER_CANDIDATES) {
            String ip = request.getHeader(header);
            if (StringUtils.isNotBlank(ip) && !"unknown".equalsIgnoreCase(ip)) {
                return ip.split(",")[0].trim();
            }
        }
        return request.getRemoteAddr();
    }

    private String extractSubnetPrefix(String ipAddress, int prefixLength) {
        if (StringUtils.isBlank(ipAddress) || ipAddress.equals("127.0.0.1") || ipAddress.equals("0:0:0:0:0:0:0:1")) {
            return ipAddress;
        }
        String[] octets = ipAddress.split("\\.");
        if (octets.length == 4) {
            return octets[0] + "." + octets[1] + "." + octets[2] + ".0/" + prefixLength;
        }
        return ipAddress;
    }

    private String resolveGeoCountry(String ipAddress) {
        return "UNKNOWN";
    }

    private String resolveGeoCity(String ipAddress) {
        return "UNKNOWN";
    }

    private String resolveGeoRegion(String ipAddress) {
        return "UNKNOWN";
    }

    private String resolveIsp(String ipAddress) {
        return "UNKNOWN";
    }

    private boolean checkProxy(String ipAddress) {
        return false;
    }

    private boolean checkVpn(String ipAddress) {
        return false;
    }

    private boolean checkTor(String ipAddress) {
        return false;
    }

    private boolean checkDataCenter(String ipAddress) {
        return false;
    }
}

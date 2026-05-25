package com.riskcontrol.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class ProxyIpCrawlerService {

    private static final Logger logger = LoggerFactory.getLogger(ProxyIpCrawlerService.class);

    private static final Pattern IP_PATTERN = Pattern.compile(
            "(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}):(\\d{2,5})");

    @Value("${riskcontrol.proxy.crawler.enabled:true}")
    private boolean crawlerEnabled;

    @Value("${riskcontrol.proxy.crawler.timeout:10000}")
    private int timeout;

    @Value("${riskcontrol.proxy.crawler.max-ips-per-source:500}")
    private int maxIpsPerSource;

    private static final List<ProxySource> PROXY_SOURCES = Arrays.asList(
            new ProxySource("https://www.sslproxies.org/", "proxy",
                    "table.table-striped tbody tr td:first-child"),
            new ProxySource("https://free-proxy-list.net/", "proxy",
                    "table.table tbody tr td:first-child"),
            new ProxySource("https://www.us-proxy.org/", "proxy",
                    "table.table tbody tr td:first-child"),
            new ProxySource("https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc",
                    "proxy", null),
            new ProxySource("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
                    "proxy", null),
            new ProxySource("https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
                    "proxy", null)
    );

    private static final List<ProxySource> VPN_SOURCES = Arrays.asList(
            new ProxySource("https://raw.githubusercontent.com/ejrv/VPNs/master/vpns-ipv4.txt",
                    "vpn", null),
            new ProxySource("https://raw.githubusercontent.com/X4BNet/lists_vpn/main/output/vpn/ipv4.txt",
                    "vpn", null)
    );

    private static final List<ProxySource> TOR_SOURCES = Arrays.asList(
            new ProxySource("https://check.torproject.org/torbulkexitlist",
                    "tor", null),
            new ProxySource("https://raw.githubusercontent.com/SecOps-Institute/Tor-IP-Addresses/master/tor-exit-nodes.lst",
                    "tor", null),
            new ProxySource("https://raw.githubusercontent.com/SecOps-Institute/Tor-IP-Addresses/master/tor-nodes.lst",
                    "tor", null),
            new ProxySource("https://www.dan.me.uk/torlist/?exit",
                    "tor", null)
    );

    public Map<String, String> crawlAllSources() {
        if (!crawlerEnabled) {
            logger.info("Proxy IP crawler is disabled");
            return Collections.emptyMap();
        }

        Map<String, String> allProxies = new HashMap<>();

        logger.info("Starting proxy IP crawl from {} sources", PROXY_SOURCES.size() + VPN_SOURCES.size() + TOR_SOURCES.size());

        for (ProxySource source : PROXY_SOURCES) {
            try {
                Map<String, String> ips = crawlSource(source);
                allProxies.putAll(ips);
                logger.debug("Crawled {} IPs from {} (type: {})", ips.size(), source.getUrl(), source.getType());
            } catch (Exception e) {
                logger.warn("Failed to crawl proxy source: {}, error: {}", source.getUrl(), e.getMessage());
            }
        }

        for (ProxySource source : VPN_SOURCES) {
            try {
                Map<String, String> ips = crawlSource(source);
                allProxies.putAll(ips);
                logger.debug("Crawled {} VPN IPs from {}", ips.size(), source.getUrl());
            } catch (Exception e) {
                logger.warn("Failed to crawl VPN source: {}, error: {}", source.getUrl(), e.getMessage());
            }
        }

        for (ProxySource source : TOR_SOURCES) {
            try {
                Map<String, String> ips = crawlSource(source);
                allProxies.putAll(ips);
                logger.debug("Crawled {} TOR IPs from {}", ips.size(), source.getUrl());
            } catch (Exception e) {
                logger.warn("Failed to crawl TOR source: {}, error: {}", source.getUrl(), e.getMessage());
            }
        }

        logger.info("Proxy IP crawl completed, total unique IPs: {}", allProxies.size());

        return allProxies;
    }

    public Map<String, String> crawlSource(ProxySource source) throws Exception {
        Map<String, String> ips = new HashMap<>();
        String content = fetchUrl(source.getUrl());

        if (content == null || content.isEmpty()) {
            return ips;
        }

        Set<String> extractedIps;
        if (source.getSelector() != null) {
            extractedIps = extractIpsFromHtml(content, source.getSelector());
        } else {
            extractedIps = extractIpsFromText(content);
        }

        int count = 0;
        for (String ip : extractedIps) {
            if (count >= maxIpsPerSource) {
                break;
            }
            if (isValidIp(ip)) {
                ips.put(ip, source.getType());
                count++;
            }
        }

        return ips;
    }

    private String fetchUrl(String urlString) throws Exception {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setConnectTimeout(timeout);
        conn.setReadTimeout(timeout);
        conn.setRequestMethod("GET");
        conn.setRequestProperty("User-Agent", "Mozilla/5.0 (compatible; RiskControlBot/1.0)");
        conn.setRequestProperty("Accept", "text/plain,text/html,application/json");

        int responseCode = conn.getResponseCode();
        if (responseCode != 200) {
            logger.debug("HTTP {} for {}", responseCode, urlString);
            return null;
        }

        StringBuilder content = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(conn.getInputStream(), "UTF-8"))) {
            String line;
            while ((line = reader.readLine()) != null) {
                content.append(line).append("\n");
            }
        }

        conn.disconnect();
        return content.toString();
    }

    private Set<String> extractIpsFromText(String text) {
        Set<String> ips = new HashSet<>();
        Matcher matcher = IP_PATTERN.matcher(text);
        while (matcher.find()) {
            String ip = matcher.group(1);
            if (isValidIp(ip)) {
                ips.add(ip);
            }
        }

        if (ips.isEmpty()) {
            for (String line : text.split("\n")) {
                line = line.trim();
                if (isValidIp(line)) {
                    ips.add(line);
                }
            }
        }

        return ips;
    }

    private Set<String> extractIpsFromHtml(String html, String selector) {
        Set<String> ips = new HashSet<>();
        Matcher matcher = IP_PATTERN.matcher(html);
        while (matcher.find()) {
            String ip = matcher.group(1);
            if (isValidIp(ip)) {
                ips.add(ip);
            }
        }
        return ips;
    }

    private boolean isValidIp(String ip) {
        if (ip == null || ip.isEmpty()) {
            return false;
        }

        String[] parts = ip.split("\\.");
        if (parts.length != 4) {
            return false;
        }

        for (String part : parts) {
            try {
                int num = Integer.parseInt(part);
                if (num < 0 || num > 255) {
                    return false;
                }
            } catch (NumberFormatException e) {
                return false;
            }
        }

        if (ip.startsWith("0.") || ip.startsWith("127.") || ip.startsWith("10.")
                || ip.startsWith("192.168.") || ip.startsWith("169.254.")
                || ip.startsWith("224.") || ip.startsWith("240.")
                || ip.startsWith("255.")) {
            return false;
        }

        if (ip.startsWith("172.")) {
            try {
                int second = Integer.parseInt(parts[1]);
                if (second >= 16 && second <= 31) {
                    return false;
                }
            } catch (NumberFormatException e) {
                return false;
            }
        }

        return true;
    }

    public Map<String, Integer> getDefaultRiskScores() {
        Map<String, Integer> scores = new HashMap<>();
        scores.put("proxy", 25);
        scores.put("vpn", 30);
        scores.put("tor", 40);
        scores.put("datacenter", 20);
        return scores;
    }

    public boolean isCrawlerEnabled() {
        return crawlerEnabled;
    }

    public static class ProxySource {
        private final String url;
        private final String type;
        private final String selector;

        public ProxySource(String url, String type, String selector) {
            this.url = url;
            this.type = type;
            this.selector = selector;
        }

        public String getUrl() { return url; }
        public String getType() { return type; }
        public String getSelector() { return selector; }
    }
}

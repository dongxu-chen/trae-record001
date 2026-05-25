package com.riskcontrol.service;

import com.riskcontrol.redis.service.IpBlacklistService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class ProxyIpUpdateService {

    private static final Logger logger = LoggerFactory.getLogger(ProxyIpUpdateService.class);

    private final ProxyIpCrawlerService crawlerService;
    private final IpBlacklistService ipBlacklistService;

    @Value("${riskcontrol.proxy.update.enabled:true}")
    private boolean updateEnabled;

    @Value("${riskcontrol.proxy.update.retain-days:7}")
    private int retainDays;

    @Autowired
    public ProxyIpUpdateService(ProxyIpCrawlerService crawlerService,
                                IpBlacklistService ipBlacklistService) {
        this.crawlerService = crawlerService;
        this.ipBlacklistService = ipBlacklistService;
    }

    @Scheduled(cron = "${riskcontrol.proxy.update.cron:0 0 3 * * ?}")
    public void scheduledUpdate() {
        if (!updateEnabled) {
            logger.info("Proxy IP auto-update is disabled");
            return;
        }

        logger.info("Starting scheduled proxy IP update");

        try {
            Map<String, String> proxies = crawlerService.crawlAllSources();

            if (!proxies.isEmpty()) {
                ipBlacklistService.batchAddProxyIps(proxies);
                logger.info("Scheduled proxy IP update completed, added {} IPs", proxies.size());
            } else {
                logger.warn("No proxy IPs crawled during scheduled update");
            }

            logProxyStats();

        } catch (Exception e) {
            logger.error("Scheduled proxy IP update failed", e);
        }
    }

    public void manualUpdate() {
        logger.info("Starting manual proxy IP update");

        try {
            Map<String, String> proxies = crawlerService.crawlAllSources();

            if (!proxies.isEmpty()) {
                ipBlacklistService.batchAddProxyIps(proxies);
                logger.info("Manual proxy IP update completed, added {} IPs", proxies.size());
            }

            return;
        } catch (Exception e) {
            logger.error("Manual proxy IP update failed", e);
            throw new RuntimeException("Failed to update proxy IPs: " + e.getMessage(), e);
        }
    }

    public void logProxyStats() {
        Map<String, Integer> stats = ipBlacklistService.getProxyStats();
        long lastUpdate = ipBlacklistService.getLastProxyUpdateTimestamp();

        logger.info("Proxy IP stats - Proxy: {}, VPN: {}, TOR: {}, Datacenter: {}, Blacklist: {}, Last update: {}",
                stats.get("proxy"), stats.get("vpn"), stats.get("tor"),
                stats.get("datacenter"), stats.get("blacklist"),
                lastUpdate > 0 ? new java.util.Date(lastUpdate) : "Never");
    }

    public Map<String, Integer> getProxyStats() {
        return ipBlacklistService.getProxyStats();
    }

    public long getLastUpdateTimestamp() {
        return ipBlacklistService.getLastProxyUpdateTimestamp();
    }
}

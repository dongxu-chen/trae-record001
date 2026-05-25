package com.riskcontrol.redis.service;

import com.riskcontrol.common.model.IpInfo;
import org.redisson.api.RBloomFilter;
import org.redisson.api.RSet;
import org.redisson.api.RMap;
import org.redisson.api.RedissonClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.TimeUnit;

@Service
public class IpBlacklistService {

    private static final Logger logger = LoggerFactory.getLogger(IpBlacklistService.class);

    private static final String IP_BLACKLIST_SET = "risk:ip:blacklist";
    private static final String IP_PROXY_SET = "risk:ip:proxy";
    private static final String IP_VPN_SET = "risk:ip:vpn";
    private static final String IP_TOR_SET = "risk:ip:tor";
    private static final String IP_DATACENTER_SET = "risk:ip:datacenter";
    private static final String IP_INFO_MAP = "risk:ip:info:";
    private static final String IP_BLOOM_FILTER = "risk:ip:bloomfilter";
    private static final String IP_PROXY_LAST_UPDATE = "risk:ip:proxy:last_update";
    private static final long IP_INFO_EXPIRE_HOURS = 24;

    private final RedissonClient redissonClient;
    private final RBloomFilter<String> ipBloomFilter;

    @Autowired
    public IpBlacklistService(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
        this.ipBloomFilter = redissonClient.getBloomFilter(IP_BLOOM_FILTER);
        if (!ipBloomFilter.isExists()) {
            ipBloomFilter.tryInit(2000000, 0.01);
        }
    }

    public void addToBlacklist(String ipAddress, String reason) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return;
        }
        RSet<String> blacklistSet = redissonClient.getSet(IP_BLACKLIST_SET);
        blacklistSet.add(ipAddress);
        ipBloomFilter.add(ipAddress);
        logger.info("Added IP {} to blacklist, reason: {}", ipAddress, reason);
    }

    public void removeFromBlacklist(String ipAddress) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return;
        }
        RSet<String> blacklistSet = redissonClient.getSet(IP_BLACKLIST_SET);
        blacklistSet.remove(ipAddress);
        logger.info("Removed IP {} from blacklist", ipAddress);
    }

    public boolean isBlacklisted(String ipAddress) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return false;
        }
        if (!ipBloomFilter.contains(ipAddress)) {
            return false;
        }
        RSet<String> blacklistSet = redissonClient.getSet(IP_BLACKLIST_SET);
        return blacklistSet.contains(ipAddress);
    }

    public void addProxyIp(String ipAddress, String proxyType, int riskScore) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return;
        }

        String setKey = IP_PROXY_SET;
        if ("vpn".equalsIgnoreCase(proxyType)) {
            setKey = IP_VPN_SET;
        } else if ("tor".equalsIgnoreCase(proxyType)) {
            setKey = IP_TOR_SET;
        } else if ("datacenter".equalsIgnoreCase(proxyType)) {
            setKey = IP_DATACENTER_SET;
        }

        RSet<String> proxySet = redissonClient.getSet(setKey);
        proxySet.add(ipAddress);
        ipBloomFilter.add(ipAddress);

        IpInfo ipInfo = getIpInfo(ipAddress);
        if (ipInfo == null) {
            ipInfo = IpInfo.builder()
                    .ipAddress(ipAddress)
                    .isProxy(true)
                    .proxyType(proxyType)
                    .riskScore(riskScore)
                    .build();
        } else {
            ipInfo.setProxy(true);
            ipInfo.setProxyType(proxyType);
            ipInfo.setRiskScore(Math.max(ipInfo.getRiskScore(), riskScore));
        }
        saveIpInfo(ipInfo);

        logger.debug("Added proxy IP {} (type: {}, score: {})", ipAddress, proxyType, riskScore);
    }

    public void batchAddProxyIps(Map<String, String> ipProxyMap) {
        if (ipProxyMap == null || ipProxyMap.isEmpty()) {
            return;
        }

        int totalAdded = 0;
        Map<String, RSet<String>> typeSets = new HashMap<>();
        typeSets.put("proxy", redissonClient.getSet(IP_PROXY_SET));
        typeSets.put("vpn", redissonClient.getSet(IP_VPN_SET));
        typeSets.put("tor", redissonClient.getSet(IP_TOR_SET));
        typeSets.put("datacenter", redissonClient.getSet(IP_DATACENTER_SET));

        for (Map.Entry<String, String> entry : ipProxyMap.entrySet()) {
            String ip = entry.getKey();
            String type = entry.getValue();

            if (ip == null || ip.isEmpty()) continue;

            RSet<String> set = typeSets.getOrDefault(type.toLowerCase(), typeSets.get("proxy"));
            set.add(ip);
            ipBloomFilter.add(ip);
            totalAdded++;

            if (totalAdded % 1000 == 0) {
                logger.debug("Batch progress: {} IPs added", totalAdded);
            }
        }

        redissonClient.getBucket(IP_PROXY_LAST_UPDATE).set(System.currentTimeMillis());

        logger.info("Batch added {} proxy IPs to the database", totalAdded);
    }

    public void removeProxyIp(String ipAddress, String proxyType) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return;
        }

        String setKey = IP_PROXY_SET;
        if ("vpn".equalsIgnoreCase(proxyType)) {
            setKey = IP_VPN_SET;
        } else if ("tor".equalsIgnoreCase(proxyType)) {
            setKey = IP_TOR_SET;
        } else if ("datacenter".equalsIgnoreCase(proxyType)) {
            setKey = IP_DATACENTER_SET;
        }

        RSet<String> proxySet = redissonClient.getSet(setKey);
        proxySet.remove(ipAddress);
        logger.debug("Removed proxy IP {} from {} set", ipAddress, proxyType);
    }

    public boolean isProxyIp(String ipAddress) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return false;
        }
        if (!ipBloomFilter.contains(ipAddress)) {
            return false;
        }

        RSet<String> proxySet = redissonClient.getSet(IP_PROXY_SET);
        if (proxySet.contains(ipAddress)) return true;

        RSet<String> vpnSet = redissonClient.getSet(IP_VPN_SET);
        if (vpnSet.contains(ipAddress)) return true;

        RSet<String> torSet = redissonClient.getSet(IP_TOR_SET);
        if (torSet.contains(ipAddress)) return true;

        RSet<String> datacenterSet = redissonClient.getSet(IP_DATACENTER_SET);
        return datacenterSet.contains(ipAddress);
    }

    public String getProxyType(String ipAddress) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return null;
        }

        RSet<String> torSet = redissonClient.getSet(IP_TOR_SET);
        if (torSet.contains(ipAddress)) return "tor";

        RSet<String> vpnSet = redissonClient.getSet(IP_VPN_SET);
        if (vpnSet.contains(ipAddress)) return "vpn";

        RSet<String> datacenterSet = redissonClient.getSet(IP_DATACENTER_SET);
        if (datacenterSet.contains(ipAddress)) return "datacenter";

        RSet<String> proxySet = redissonClient.getSet(IP_PROXY_SET);
        if (proxySet.contains(ipAddress)) return "proxy";

        return null;
    }

    public void saveIpInfo(IpInfo ipInfo) {
        if (ipInfo == null || ipInfo.getIpAddress() == null) {
            return;
        }

        String key = IP_INFO_MAP + ipInfo.getIpAddress();
        RMap<String, Object> ipMap = redissonClient.getMap(key);

        ipInfo.setLastCheckTimestamp(System.currentTimeMillis());

        ipMap.put("ipAddress", ipInfo.getIpAddress());
        ipMap.put("country", ipInfo.getCountry());
        ipMap.put("region", ipInfo.getRegion());
        ipMap.put("city", ipInfo.getCity());
        ipMap.put("latitude", ipInfo.getLatitude());
        ipMap.put("longitude", ipInfo.getLongitude());
        ipMap.put("isp", ipInfo.getIsp());
        ipMap.put("organization", ipInfo.getOrganization());
        ipMap.put("asn", ipInfo.getAsn());
        ipMap.put("isProxy", ipInfo.isProxy());
        ipMap.put("isVpn", ipInfo.isVpn());
        ipMap.put("isTor", ipInfo.isTor());
        ipMap.put("isDataCenter", ipInfo.isDataCenter());
        ipMap.put("isBlacklisted", ipInfo.isBlacklisted());
        ipMap.put("riskScore", ipInfo.getRiskScore());
        ipMap.put("proxyType", ipInfo.getProxyType());
        ipMap.put("lastCheckTimestamp", ipInfo.getLastCheckTimestamp());

        ipMap.expire(IP_INFO_EXPIRE_HOURS, TimeUnit.HOURS);

        logger.debug("Saved IP info for: {}", ipInfo.getIpAddress());
    }

    public IpInfo getIpInfo(String ipAddress) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return null;
        }

        String key = IP_INFO_MAP + ipAddress;
        RMap<String, Object> ipMap = redissonClient.getMap(key);

        if (ipMap.isEmpty()) {
            return null;
        }

        IpInfo ipInfo = IpInfo.builder()
                .ipAddress((String) ipMap.get("ipAddress"))
                .country((String) ipMap.get("country"))
                .region((String) ipMap.get("region"))
                .city((String) ipMap.get("city"))
                .latitude(ipMap.get("latitude") != null ? (Double) ipMap.get("latitude") : 0.0)
                .longitude(ipMap.get("longitude") != null ? (Double) ipMap.get("longitude") : 0.0)
                .isp((String) ipMap.get("isp"))
                .organization((String) ipMap.get("organization"))
                .asn((String) ipMap.get("asn"))
                .isProxy(ipMap.get("isProxy") != null && (Boolean) ipMap.get("isProxy"))
                .isVpn(ipMap.get("isVpn") != null && (Boolean) ipMap.get("isVpn"))
                .isTor(ipMap.get("isTor") != null && (Boolean) ipMap.get("isTor"))
                .isDataCenter(ipMap.get("isDataCenter") != null && (Boolean) ipMap.get("isDataCenter"))
                .isBlacklisted(ipMap.get("isBlacklisted") != null && (Boolean) ipMap.get("isBlacklisted"))
                .riskScore(ipMap.get("riskScore") != null ? (Integer) ipMap.get("riskScore") : 0)
                .proxyType((String) ipMap.get("proxyType"))
                .lastCheckTimestamp(ipMap.get("lastCheckTimestamp") != null ?
                        (Long) ipMap.get("lastCheckTimestamp") : 0)
                .build();

        if (isProxyIp(ipAddress) && !ipInfo.isProxy()) {
            ipInfo.setProxy(true);
            ipInfo.setProxyType(getProxyType(ipAddress));
        }

        return ipInfo;
    }

    public int getIpRiskScore(String ipAddress) {
        IpInfo ipInfo = getIpInfo(ipAddress);
        if (ipInfo == null) {
            return 0;
        }

        int score = ipInfo.getRiskScore();
        if (ipInfo.isBlacklisted()) score = Math.max(score, 50);
        if (ipInfo.isTor()) score = Math.max(score, 40);
        if (ipInfo.isVpn()) score = Math.max(score, 30);
        if (ipInfo.isProxy()) score = Math.max(score, 25);
        if (ipInfo.isDataCenter()) score = Math.max(score, 20);

        return Math.min(score, 100);
    }

    public long getLastProxyUpdateTimestamp() {
        Object value = redissonClient.getBucket(IP_PROXY_LAST_UPDATE).get();
        if (value instanceof Long) {
            return (Long) value;
        }
        return 0;
    }

    public int getTotalProxyCount() {
        RSet<String> proxySet = redissonClient.getSet(IP_PROXY_SET);
        RSet<String> vpnSet = redissonClient.getSet(IP_VPN_SET);
        RSet<String> torSet = redissonClient.getSet(IP_TOR_SET);
        RSet<String> datacenterSet = redissonClient.getSet(IP_DATACENTER_SET);

        return proxySet.size() + vpnSet.size() + torSet.size() + datacenterSet.size();
    }

    public Map<String, Integer> getProxyStats() {
        Map<String, Integer> stats = new HashMap<>();
        stats.put("proxy", redissonClient.getSet(IP_PROXY_SET).size());
        stats.put("vpn", redissonClient.getSet(IP_VPN_SET).size());
        stats.put("tor", redissonClient.getSet(IP_TOR_SET).size());
        stats.put("datacenter", redissonClient.getSet(IP_DATACENTER_SET).size());
        stats.put("blacklist", redissonClient.getSet(IP_BLACKLIST_SET).size());
        return stats;
    }
}

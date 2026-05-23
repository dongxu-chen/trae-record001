package com.shortlink.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.shortlink.dto.IpLocationResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import jakarta.annotation.PostConstruct;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class IpLocationService {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${amap.api.key:}")
    private String amapApiKey;

    @Value("${amap.api.enabled:true}")
    private boolean amapEnabled;

    @Value("${ip.cache.expire-minutes:1440}")
    private int cacheExpireMinutes;

    @Value("${ip.cache.max-size:10000}")
    private int cacheMaxSize;

    private LoadingCache<String, IpLocationResult> ipCache;

    private static final String AMAP_API_URL = "https://restapi.amap.com/v3/ip";

    public IpLocationService(RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void init() {
        ipCache = CacheBuilder.newBuilder()
                .expireAfterWrite(cacheExpireMinutes, TimeUnit.MINUTES)
                .maximumSize(cacheMaxSize)
                .build(new CacheLoader<String, IpLocationResult>() {
                    @Override
                    public IpLocationResult load(String ip) throws Exception {
                        return fetchIpLocation(ip);
                    }
                });
    }

    public IpLocationResult getLocation(String ip) {
        if (ip == null || ip.isBlank() || "0:0:0:0:0:0:0:1".equals(ip) || "127.0.0.1".equals(ip)) {
            return new IpLocationResult("本地", "本地", "本地");
        }

        try {
            return ipCache.getUnchecked(ip);
        } catch (Exception e) {
            log.warn("获取IP地理位置失败: {}, error: {}", ip, e.getMessage());
            return new IpLocationResult("未知", "未知", "未知");
        }
    }

    private IpLocationResult fetchIpLocation(String ip) {
        if (!amapEnabled || amapApiKey == null || amapApiKey.isBlank()) {
            return new IpLocationResult("未知", "未知", "未知");
        }

        try {
            String url = UriComponentsBuilder.fromHttpUrl(AMAP_API_URL)
                    .queryParam("key", amapApiKey)
                    .queryParam("ip", ip)
                    .queryParam("output", "json")
                    .toUriString();

            String response = restTemplate.getForObject(url, String.class);

            if (response == null) {
                return new IpLocationResult("未知", "未知", "未知");
            }

            JsonNode root = objectMapper.readTree(response);
            String status = root.path("status").asText();

            if (!"1".equals(status)) {
                log.warn("高德IP查询返回错误: {}, ip: {}", root.path("info").asText(), ip);
                return new IpLocationResult("未知", "未知", "未知");
            }

            IpLocationResult result = new IpLocationResult();
            result.setCountry("中国");
            result.setProvince(root.path("province").asText("未知"));
            result.setCity(root.path("city").asText("未知"));
            result.setIsp(root.path("isp").asText(""));

            log.debug("IP地理位置查询成功: {} -> {}, {}, {}", ip, result.getProvince(), result.getCity(), result.getIsp());
            return result;

        } catch (Exception e) {
            log.warn("调用高德IP查询API失败: {}, error: {}", ip, e.getMessage());
            return new IpLocationResult("未知", "未知", "未知");
        }
    }

    public void invalidateCache(String ip) {
        ipCache.invalidate(ip);
    }

    public void invalidateAllCache() {
        ipCache.invalidateAll();
    }

    public long getCacheSize() {
        return ipCache.size();
    }
}

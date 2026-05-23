package com.configcenter.service;

import com.configcenter.dto.GrayReleaseDTO;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class GrayReleaseService {

    private final Map<String, GrayReleaseDTO> grayReleases = new ConcurrentHashMap<>();

    public GrayReleaseDTO createGrayRelease(GrayReleaseDTO request) {
        String id = UUID.randomUUID().toString();
        GrayReleaseDTO grayRelease = new GrayReleaseDTO();
        grayRelease.setId(id);
        grayRelease.setApplication(request.getApplication());
        grayRelease.setProfile(request.getProfile());
        grayRelease.setGrayVersion(UUID.randomUUID().toString());
        grayRelease.setStableVersion(request.getStableVersion());
        grayRelease.setStrategy(request.getStrategy());
        grayRelease.setPercentage(request.getPercentage());
        grayRelease.setIpList(request.getIpList());
        grayRelease.setContent(request.getContent());
        grayRelease.setFormat(request.getFormat());
        grayRelease.setDescription(request.getDescription());
        grayRelease.setCreateTime(LocalDateTime.now());
        grayRelease.setCreatedBy(request.getCreatedBy() != null ? request.getCreatedBy() : "system");
        grayRelease.setExpireTime(request.getExpireTime() != null ? request.getExpireTime() :
                LocalDateTime.now().plusHours(24));
        grayRelease.setEnabled(true);

        grayReleases.put(id, grayRelease);
        return grayRelease;
    }

    public boolean shouldUseGrayConfig(String application, String profile, String clientIp) {
        List<GrayReleaseDTO> activeGrays = grayReleases.values().stream()
                .filter(g -> g.getApplication().equals(application))
                .filter(g -> g.getProfile().equals(profile))
                .filter(g -> g.isEnabled())
                .filter(g -> g.getExpireTime().isAfter(LocalDateTime.now()))
                .collect(Collectors.toList());

        if (activeGrays.isEmpty()) {
            return false;
        }

        for (GrayReleaseDTO gray : activeGrays) {
            if (matchGrayStrategy(gray, clientIp)) {
                return true;
            }
        }
        return false;
    }

    private boolean matchGrayStrategy(GrayReleaseDTO grayRelease, String clientIp) {
        switch (grayRelease.getStrategy()) {
            case IP_LIST:
                return grayRelease.getIpList() != null && grayRelease.getIpList().contains(clientIp);
            case PERCENTAGE:
                int hash = Math.abs(clientIp.hashCode());
                return (hash % 100) < grayRelease.getPercentage();
            default:
                return false;
        }
    }

    public GrayReleaseDTO getGrayRelease(String application, String profile, String clientIp) {
        List<GrayReleaseDTO> activeGrays = grayReleases.values().stream()
                .filter(g -> g.getApplication().equals(application))
                .filter(g -> g.getProfile().equals(profile))
                .filter(g -> g.isEnabled())
                .filter(g -> g.getExpireTime().isAfter(LocalDateTime.now()))
                .collect(Collectors.toList());

        for (GrayReleaseDTO gray : activeGrays) {
            if (matchGrayStrategy(gray, clientIp)) {
                return gray;
            }
        }
        return null;
    }

    public GrayReleaseDTO getGrayReleaseById(String id) {
        return grayReleases.get(id);
    }

    public List<GrayReleaseDTO> listGrayReleases(String application, String profile) {
        return grayReleases.values().stream()
                .filter(g -> application == null || g.getApplication().equals(application))
                .filter(g -> profile == null || g.getProfile().equals(profile))
                .collect(Collectors.toList());
    }

    public GrayReleaseDTO updateGrayRelease(String id, GrayReleaseDTO request) {
        GrayReleaseDTO existing = grayReleases.get(id);
        if (existing == null) {
            return null;
        }

        if (request.getPercentage() > 0) {
            existing.setPercentage(request.getPercentage());
        }
        if (request.getIpList() != null) {
            existing.setIpList(request.getIpList());
        }
        if (request.getExpireTime() != null) {
            existing.setExpireTime(request.getExpireTime());
        }
        if (request.getContent() != null) {
            existing.setContent(request.getContent());
        }

        return existing;
    }

    public boolean stopGrayRelease(String id) {
        GrayReleaseDTO gray = grayReleases.get(id);
        if (gray != null) {
            gray.setEnabled(false);
            return true;
        }
        return false;
    }

    public boolean deleteGrayRelease(String id) {
        return grayReleases.remove(id) != null;
    }

    public Map<String, Object> getGrayReleaseStats(String id) {
        GrayReleaseDTO gray = grayReleases.get(id);
        if (gray == null) {
            return null;
        }

        Map<String, Object> stats = new ConcurrentHashMap<>();
        stats.put("id", gray.getId());
        stats.put("application", gray.getApplication());
        stats.put("profile", gray.getProfile());
        stats.put("strategy", gray.getStrategy());
        stats.put("percentage", gray.getPercentage());
        stats.put("ipCount", gray.getIpList() != null ? gray.getIpList().size() : 0);
        stats.put("enabled", gray.isEnabled());
        stats.put("createTime", gray.getCreateTime());
        stats.put("expireTime", gray.getExpireTime());
        stats.put("remainingHours",
                java.time.Duration.between(LocalDateTime.now(), gray.getExpireTime()).toHours());

        return stats;
    }

    public GrayReleaseDTO fullGrayRelease(String id) {
        GrayReleaseDTO gray = grayReleases.get(id);
        if (gray == null) {
            return null;
        }
        gray.setPercentage(100);
        gray.setStrategy(GrayReleaseDTO.GrayStrategy.PERCENTAGE);
        return gray;
    }
}

package com.pushcenter.service;

import com.pushcenter.channel.ChannelHandlerFactory;
import com.pushcenter.enums.PushChannel;
import com.pushcenter.model.PushTemplate;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.*;

@Slf4j
@Service
public class ChannelSelectorService {

    @Resource
    private UserConfigService userConfigService;

    @Resource
    private ChannelHandlerFactory channelHandlerFactory;

    @Resource
    private RateLimitService rateLimitService;

    @Resource
    private ChannelHealthService channelHealthService;

    public PushChannel selectOptimalChannel(String userId, PushTemplate template, PushChannel preferredChannel) {
        Set<PushChannel> supportedChannels = template.getSupportedChannels();
        if (supportedChannels == null || supportedChannels.isEmpty()) {
            log.warn("No supported channels for template: {}", template.getTemplateCode());
            return null;
        }

        if (preferredChannel != null) {
            if (channelHealthService.isDegraded(preferredChannel)) {
                log.info("Preferred channel {} is degraded, trying fallback", preferredChannel);
                PushChannel fallback = channelHealthService.getFallbackChannel(preferredChannel, supportedChannels);
                if (fallback != null && isChannelAvailable(userId, template, fallback)) {
                    return fallback;
                }
            }
            if (isChannelAvailable(userId, template, preferredChannel)) {
                log.debug("Using preferred channel: {} for user: {}", preferredChannel, userId);
                return preferredChannel;
            }
        }

        List<PushChannel> userPreferred = userConfigService.getPreferredChannels(userId);
        if (userPreferred != null && !userPreferred.isEmpty()) {
            for (PushChannel channel : userPreferred) {
                if (channelHealthService.isDegraded(channel)) {
                    log.debug("Channel {} is degraded, skipping", channel);
                    continue;
                }
                if (isChannelAvailable(userId, template, channel)) {
                    log.debug("Selected user preferred channel: {} for user: {}", channel, userId);
                    return channel;
                }
            }
        }

        PushChannel defaultChannel = template.getDefaultChannel();
        if (defaultChannel != null && !channelHealthService.isDegraded(defaultChannel)
                && isChannelAvailable(userId, template, defaultChannel)) {
            log.debug("Using template default channel: {} for user: {}", defaultChannel, userId);
            return defaultChannel;
        }

        List<PushChannel> sortedChannels = new ArrayList<>(supportedChannels);
        sortedChannels.sort((a, b) -> {
            boolean aDegraded = channelHealthService.isDegraded(a);
            boolean bDegraded = channelHealthService.isDegraded(b);
            if (aDegraded != bDegraded) {
                return aDegraded ? 1 : -1;
            }
            return Integer.compare(a.getPriority(), b.getPriority());
        });

        for (PushChannel channel : sortedChannels) {
            if (!channelHealthService.isDegraded(channel) && isChannelAvailable(userId, template, channel)) {
                log.debug("Selected channel: {} for user: {}", channel, userId);
                return channel;
            }
        }

        for (PushChannel channel : sortedChannels) {
            if (isChannelAvailable(userId, template, channel)) {
                log.warn("All non-degraded channels exhausted, using degraded channel: {} for user: {}",
                        channel, userId);
                return channel;
            }
        }

        log.warn("No available channel found for user: {}, template: {}", userId, template.getTemplateCode());
        return null;
    }

    private boolean isChannelAvailable(String userId, PushTemplate template, PushChannel channel) {
        if (!template.getSupportedChannels().contains(channel)) {
            return false;
        }

        if (userConfigService.isChannelDisabled(userId, channel)) {
            return false;
        }

        String receiver = userConfigService.getReceiverForChannel(userId, channel);
        if (receiver == null || receiver.isEmpty()) {
            return false;
        }

        if (!channelHandlerFactory.isChannelAvailable(channel)) {
            return false;
        }

        return true;
    }

    public List<PushChannel> getAvailableChannels(String userId, PushTemplate template) {
        List<PushChannel> available = new ArrayList<>();
        for (PushChannel channel : template.getSupportedChannels()) {
            if (isChannelAvailable(userId, template, channel)) {
                available.add(channel);
            }
        }
        return available;
    }

    public boolean isChannelHealthy(PushChannel channel) {
        return !channelHealthService.isDegraded(channel);
    }
}

package com.pushcenter.service;

import com.pushcenter.enums.PushChannel;
import com.pushcenter.model.UserChannelConfig;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class UserConfigService {

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    private final Map<String, UserChannelConfig> localCache = new ConcurrentHashMap<>();

    private static final String USER_CONFIG_PREFIX = "push_center:user_config:";
    private static final long CACHE_TTL_SECONDS = 300;

    public UserChannelConfig getUserConfig(String userId) {
        UserChannelConfig config = localCache.get(userId);
        if (config != null) {
            return config;
        }

        config = (UserChannelConfig) redisTemplate.opsForValue().get(USER_CONFIG_PREFIX + userId);
        if (config != null) {
            localCache.put(userId, config);
        }

        return config;
    }

    public void saveUserConfig(UserChannelConfig config) {
        redisTemplate.opsForValue().set(USER_CONFIG_PREFIX + config.getUserId(), config, CACHE_TTL_SECONDS, TimeUnit.SECONDS);
        localCache.put(config.getUserId(), config);
        log.info("User config saved: {}", config.getUserId());
    }

    public String getReceiverForChannel(String userId, PushChannel channel) {
        UserChannelConfig config = getUserConfig(userId);
        if (config == null || config.getChannelReceivers() == null) {
            return null;
        }
        return config.getChannelReceivers().get(channel);
    }

    public List<PushChannel> getPreferredChannels(String userId) {
        UserChannelConfig config = getUserConfig(userId);
        if (config == null || config.getPreferredChannels() == null) {
            return Collections.emptyList();
        }
        return config.getPreferredChannels();
    }

    public boolean isChannelDisabled(String userId, PushChannel channel) {
        UserChannelConfig config = getUserConfig(userId);
        if (config == null || config.getDisabledChannels() == null) {
            return false;
        }
        return config.getDisabledChannels().contains(channel);
    }

    @PostConstruct
    public void initSampleData() {
        UserChannelConfig sampleUser1 = UserChannelConfig.builder()
                .userId("user001")
                .channelReceivers(new EnumMap<PushChannel, String>(PushChannel.class) {{
                    put(PushChannel.EMAIL, "user001@example.com");
                    put(PushChannel.SMS, "13800138001");
                    put(PushChannel.DINGTALK, "dingtalk_user001");
                    put(PushChannel.WECHAT_WORK, "wechat_user001");
                    put(PushChannel.APP_PUSH, "device_token_001");
                }})
                .preferredChannels(Arrays.asList(PushChannel.APP_PUSH, PushChannel.WECHAT_WORK, PushChannel.SMS))
                .disabledChannels(Collections.emptyList())
                .timezone("Asia/Shanghai")
                .build();
        saveUserConfig(sampleUser1);

        UserChannelConfig sampleUser2 = UserChannelConfig.builder()
                .userId("user002")
                .channelReceivers(new EnumMap<PushChannel, String>(PushChannel.class) {{
                    put(PushChannel.EMAIL, "user002@example.com");
                    put(PushChannel.SMS, "13800138002");
                    put(PushChannel.DINGTALK, "dingtalk_user002");
                }})
                .preferredChannels(Arrays.asList(PushChannel.SMS, PushChannel.EMAIL))
                .disabledChannels(Collections.singletonList(PushChannel.APP_PUSH))
                .timezone("Asia/Shanghai")
                .build();
        saveUserConfig(sampleUser2);

        log.info("Sample user configs initialized");
    }
}

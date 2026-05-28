package com.voting.service;

import com.voting.repository.VoteRecordRepository;
import com.voting.util.DeviceFingerprintUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.concurrent.TimeUnit;

@Service
public class AntiFraudService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private VoteRecordRepository voteRecordRepository;

    @Value("${voting.anti-fraud.ip-limit:5}")
    private int ipLimit;

    @Value("${voting.anti-fraud.ip-time-window:3600}")
    private int ipTimeWindow;

    @Value("${voting.anti-fraud.device-limit:1}")
    private int deviceLimit;

    @Value("${voting.anti-fraud.device-time-window:86400}")
    private int deviceTimeWindow;

    private static final String IP_KEY_PREFIX = "vote:ip:";
    private static final String DEVICE_KEY_PREFIX = "vote:device:";

    public boolean checkIpLimit(Long voteId, String ipAddress) {
        String ipPrefix = DeviceFingerprintUtil.getIpPrefixForLimit(ipAddress);
        String key = IP_KEY_PREFIX + voteId + ":" + ipPrefix;

        Long count = redisTemplate.opsForValue().increment(key);
        if (count == 1) {
            redisTemplate.expire(key, ipTimeWindow, TimeUnit.SECONDS);
        }

        if (count > ipLimit) {
            return false;
        }

        LocalDateTime timeThreshold = LocalDateTime.now().minusSeconds(ipTimeWindow);
        Long dbCount = voteRecordRepository.countByVoteIdAndIpAddressAndTimeAfter(voteId, ipPrefix, timeThreshold);

        return dbCount < ipLimit;
    }

    public boolean checkDeviceLimit(Long voteId, String deviceFingerprint) {
        if (deviceFingerprint == null || deviceFingerprint.isEmpty()) {
            return true;
        }

        String key = DEVICE_KEY_PREFIX + voteId + ":" + deviceFingerprint;

        Boolean isNew = redisTemplate.opsForValue().setIfAbsent(key, "1", deviceTimeWindow, TimeUnit.SECONDS);
        if (isNew == null || !isNew) {
            return false;
        }

        Long dbCount = voteRecordRepository.countByVoteIdAndDeviceFingerprint(voteId, deviceFingerprint);
        return dbCount < deviceLimit;
    }

    public boolean canVote(Long voteId, String ipAddress, String deviceFingerprint) {
        boolean ipOk = checkIpLimit(voteId, ipAddress);
        boolean deviceOk = checkDeviceLimit(voteId, deviceFingerprint);
        return ipOk && deviceOk;
    }

    public void recordVote(Long voteId, String ipAddress, String deviceFingerprint) {
        String ipPrefix = DeviceFingerprintUtil.getIpPrefixForLimit(ipAddress);
        String ipKey = IP_KEY_PREFIX + voteId + ":" + ipPrefix;
        redisTemplate.opsForValue().increment(ipKey);
        redisTemplate.expire(ipKey, ipTimeWindow, TimeUnit.SECONDS);

        if (deviceFingerprint != null && !deviceFingerprint.isEmpty()) {
            String deviceKey = DEVICE_KEY_PREFIX + voteId + ":" + deviceFingerprint;
            redisTemplate.opsForValue().set(deviceKey, "1", deviceTimeWindow, TimeUnit.SECONDS);
        }
    }
}

package com.filetransfer.service;

import com.filetransfer.entity.User;
import com.filetransfer.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class StorageQuotaService {
    private final UserRepository userRepository;

    @Value("${user.default-quota:10737418240}")
    private Long defaultQuota;

    public boolean checkQuota(Long userId, Long fileSize) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        Long quota = user.getStorageQuota() != null ? user.getStorageQuota() : defaultQuota;
        Long used = user.getUsedStorage() != null ? user.getUsedStorage() : 0L;

        return (used + fileSize) <= quota;
    }

    @Transactional
    public void increaseUsage(Long userId, Long fileSize) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        Long currentUsed = user.getUsedStorage() != null ? user.getUsedStorage() : 0L;
        user.setUsedStorage(currentUsed + fileSize);
        userRepository.save(user);

        log.info("用户 {} 存储空间增加: {}, 当前使用: {}", userId, fileSize, user.getUsedStorage());
    }

    @Transactional
    public void decreaseUsage(Long userId, Long fileSize) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        Long currentUsed = user.getUsedStorage() != null ? user.getUsedStorage() : 0L;
        user.setUsedStorage(Math.max(0L, currentUsed - fileSize));
        userRepository.save(user);

        log.info("用户 {} 存储空间减少: {}, 当前使用: {}", userId, fileSize, user.getUsedStorage());
    }

    public Long getUsedStorage(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        return user.getUsedStorage() != null ? user.getUsedStorage() : 0L;
    }

    public Long getQuota(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        return user.getStorageQuota() != null ? user.getStorageQuota() : defaultQuota;
    }

    @Transactional
    public void setQuota(Long userId, Long quota) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        user.setStorageQuota(quota);
        userRepository.save(user);
        log.info("用户 {} 存储空间配额设置为: {}", userId, quota);
    }
}

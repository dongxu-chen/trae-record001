package com.filestorage.service;

import com.filestorage.dto.FileShareDTO;
import com.filestorage.entity.FileShare;
import com.filestorage.repository.FileShareRepository;
import com.filestorage.util.FileUtil;
import com.filestorage.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import jakarta.annotation.Resource;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class FileShareService {

    private static final String SHARE_CACHE_PREFIX = "share:";

    @Resource
    private FileShareRepository fileShareRepository;

    @Resource
    private FileService fileService;

    @Resource
    private TenantService tenantService;

    @Resource
    private RedisUtil redisUtil;

    @Resource
    private MinioStorageService minioStorageService;

    @Transactional
    public Map<String, Object> createShare(FileShareDTO dto) {
        fileService.getFileById(dto.getTenantCode(), dto.getFileId());

        String shareCode = FileUtil.generateShareCode();
        String extractCode = dto.getExtractCode();
        if (extractCode == null || extractCode.isEmpty()) {
            extractCode = FileUtil.generateExtractCode();
        }

        FileShare fileShare = new FileShare();
        fileShare.setTenantId(tenantService.getTenantByCode(dto.getTenantCode()).getId());
        fileShare.setFileId(dto.getFileId());
        fileShare.setShareCode(shareCode);
        fileShare.setExtractCode(extractCode);
        fileShare.setShareUser(dto.getShareUser());
        fileShare.setViewCount(0);
        fileShare.setDownloadCount(0);
        fileShare.setStatus(1);

        if (dto.getExpireHours() != null && dto.getExpireHours() > 0) {
            fileShare.setExpireAt(LocalDateTime.now().plusHours(dto.getExpireHours()));
        }

        fileShare = fileShareRepository.save(fileShare);

        Map<String, Object> result = new HashMap<>();
        result.put("shareCode", shareCode);
        result.put("extractCode", extractCode);
        result.put("expireAt", fileShare.getExpireAt());
        result.put("id", fileShare.getId());

        return result;
    }

    public Map<String, Object> getShareInfo(String shareCode, String extractCode) {
        FileShare fileShare = getValidShare(shareCode, extractCode);

        fileShare.setViewCount(fileShare.getViewCount() + 1);
        fileShareRepository.save(fileShare);

        Map<String, Object> result = new HashMap<>();
        result.put("fileId", fileShare.getFileId());
        result.put("shareUser", fileShare.getShareUser());
        result.put("viewCount", fileShare.getViewCount());
        result.put("downloadCount", fileShare.getDownloadCount());
        result.put("expireAt", fileShare.getExpireAt());
        result.put("createdAt", fileShare.getCreatedAt());

        return result;
    }

    public String getShareDownloadUrl(String shareCode, String extractCode, int expiresInSeconds) {
        FileShare fileShare = getValidShare(shareCode, extractCode);
        fileShare.setDownloadCount(fileShare.getDownloadCount() + 1);
        fileShareRepository.save(fileShare);

        com.filestorage.entity.FileInfo fileInfo = fileService.getFileById(fileShare.getFileId());

        String bucketName = minioStorageService.getBucketName(
                tenantService.getTenantByCode(fileShare.getTenantId().toString()).getTenantCode()
        );

        return minioStorageService.getPresignedUrl(bucketName, fileInfo.getFilePath(), expiresInSeconds);
    }

    private FileShare getValidShare(String shareCode, String extractCode) {
        String cacheKey = SHARE_CACHE_PREFIX + shareCode;
        FileShare fileShare = (FileShare) redisUtil.get(cacheKey);

        if (fileShare == null) {
            fileShare = fileShareRepository.findByShareCode(shareCode)
                    .orElseThrow(() -> new RuntimeException("分享链接不存在"));
            redisUtil.set(cacheKey, fileShare, 1, TimeUnit.HOURS);
        }

        if (fileShare.getStatus() != 1) {
            throw new RuntimeException("分享链接已失效");
        }

        if (fileShare.getExpireAt() != null && fileShare.getExpireAt().isBefore(LocalDateTime.now())) {
            fileShare.setStatus(0);
            fileShareRepository.save(fileShare);
            redisUtil.delete(cacheKey);
            throw new RuntimeException("分享链接已过期");
        }

        if (!fileShare.getExtractCode().equals(extractCode)) {
            throw new RuntimeException("提取码错误");
        }

        return fileShare;
    }

    public Page<FileShare> getShareList(String tenantCode, Pageable pageable) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        return fileShareRepository.findByTenantIdAndStatus(tenantId, 1, pageable);
    }

    @Transactional
    public void cancelShare(String tenantCode, Long shareId) {
        FileShare fileShare = fileShareRepository.findById(shareId)
                .orElseThrow(() -> new RuntimeException("分享不存在"));

        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        if (!fileShare.getTenantId().equals(tenantId)) {
            throw new RuntimeException("无权限操作");
        }

        fileShare.setStatus(0);
        fileShareRepository.save(fileShare);
        redisUtil.delete(SHARE_CACHE_PREFIX + fileShare.getShareCode());
    }

    @Transactional
    public void expireShares() {
        log.info("开始清理过期的分享链接");
        int expired = fileShareRepository.expireShares(LocalDateTime.now());
        log.info("清理完成，过期分享链接: {}", expired);
    }
}

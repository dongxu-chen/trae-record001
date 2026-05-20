package com.filestorage.service;

import com.filestorage.entity.FileInfo;
import com.filestorage.repository.FileInfoRepository;
import com.filestorage.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import jakarta.annotation.Resource;
import java.io.InputStream;

@Slf4j
@Service
public class FileService {

    private static final String FILE_CACHE_PREFIX = "file:info:";

    @Resource
    private FileInfoRepository fileInfoRepository;

    @Resource
    private MinioStorageService minioStorageService;

    @Resource
    private TenantService tenantService;

    @Resource
    private RedisUtil redisUtil;

    public FileInfo getFileById(String tenantCode, Long fileId) {
        String cacheKey = FILE_CACHE_PREFIX + tenantCode + ":" + fileId;
        Object cached = redisUtil.get(cacheKey);
        if (cached != null) {
            return (FileInfo) cached;
        }

        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        FileInfo fileInfo = fileInfoRepository.findByTenantIdAndIdAndIsDeleted(tenantId, fileId, 0)
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        redisUtil.set(cacheKey, fileInfo, 1, java.util.concurrent.TimeUnit.HOURS);
        return fileInfo;
    }

    public FileInfo getFileById(Long fileId) {
        return fileInfoRepository.findByIdAndIsDeleted(fileId, 0)
                .orElseThrow(() -> new RuntimeException("文件不存在"));
    }

    public Page<FileInfo> getFileList(String tenantCode, Pageable pageable) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        return fileInfoRepository.findByTenantIdAndIsDeleted(tenantId, 0, pageable);
    }

    public InputStream downloadFile(String tenantCode, Long fileId) {
        FileInfo fileInfo = getFileById(tenantCode, fileId);
        String bucketName = minioStorageService.getBucketName(tenantCode);
        return minioStorageService.downloadFile(bucketName, fileInfo.getFilePath());
    }

    public String getDownloadUrl(String tenantCode, Long fileId, int expiresInSeconds) {
        FileInfo fileInfo = getFileById(tenantCode, fileId);
        String bucketName = minioStorageService.getBucketName(tenantCode);
        return minioStorageService.getPresignedUrl(bucketName, fileInfo.getFilePath(), expiresInSeconds);
    }

    @Transactional
    public void deleteFile(String tenantCode, Long fileId, String deleteUser) {
        FileInfo fileInfo = getFileById(tenantCode, fileId);
        fileInfo.setIsDeleted(1);
        fileInfoRepository.save(fileInfo);

        String cacheKey = FILE_CACHE_PREFIX + tenantCode + ":" + fileId;
        redisUtil.delete(cacheKey);
        redisUtil.delete("fastcheck:" + tenantCode + ":" + fileInfo.getFileMd5());
    }

    @Transactional
    public void restoreFile(String tenantCode, Long fileId) {
        FileInfo fileInfo = fileInfoRepository.findByTenantIdAndIdAndIsDeleted(
                        tenantService.getTenantByCode(tenantCode).getId(), fileId, 1)
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        fileInfo.setIsDeleted(0);
        fileInfoRepository.save(fileInfo);

        String cacheKey = FILE_CACHE_PREFIX + tenantCode + ":" + fileId;
        redisUtil.delete(cacheKey);
    }

    @Transactional
    public void permanentlyDeleteFile(String tenantCode, Long fileId) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        FileInfo fileInfo = fileInfoRepository.findById(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        String bucketName = minioStorageService.getBucketName(tenantCode);
        try {
            minioStorageService.deleteFile(bucketName, fileInfo.getFilePath());
            if (fileInfo.getHasThumbnail() == 1 && fileInfo.getThumbnailPath() != null) {
                minioStorageService.deleteFile(bucketName, fileInfo.getThumbnailPath());
            }
        } catch (Exception e) {
            log.error("删除物理文件失败", e);
        }

        tenantService.decreaseUsedStorage(tenantCode, fileInfo.getFileSize());
        fileInfoRepository.delete(fileInfo);

        String cacheKey = FILE_CACHE_PREFIX + tenantCode + ":" + fileId;
        redisUtil.delete(cacheKey);
    }

    public boolean fileExists(String tenantCode, String fileMd5) {
        String fastCheckKey = "fastcheck:" + tenantCode + ":" + fileMd5;
        if (redisUtil.hasKey(fastCheckKey)) {
            return true;
        }

        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        return !fileInfoRepository.findByTenantIdAndFileMd5AndIsDeleted(tenantId, fileMd5, 0).isEmpty();
    }
}

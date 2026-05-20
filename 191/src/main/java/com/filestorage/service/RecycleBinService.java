package com.filestorage.service;

import com.filestorage.config.FileStorageConfig;
import com.filestorage.entity.FileInfo;
import com.filestorage.entity.RecycleBin;
import com.filestorage.repository.FileInfoRepository;
import com.filestorage.repository.RecycleBinRepository;
import com.filestorage.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import jakarta.annotation.Resource;
import java.time.LocalDateTime;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class RecycleBinService {

    private static final String RECYCLE_TTL_PREFIX = "recycle:ttl:";

    @Resource
    private RecycleBinRepository recycleBinRepository;

    @Resource
    private FileInfoRepository fileInfoRepository;

    @Resource
    private FileService fileService;

    @Resource
    private TenantService tenantService;

    @Resource
    private FileStorageConfig fileStorageConfig;

    @Resource
    private RedisUtil redisUtil;

    @Transactional
    public void moveToRecycleBin(String tenantCode, Long fileId, String deleteUser) {
        FileInfo fileInfo = fileService.getFileById(tenantCode, fileId);

        fileInfo.setIsDeleted(1);
        fileInfoRepository.save(fileInfo);

        RecycleBin recycleBin = new RecycleBin();
        recycleBin.setTenantId(tenantService.getTenantByCode(tenantCode).getId());
        recycleBin.setFileId(fileId);
        recycleBin.setFileName(fileInfo.getFileName());
        recycleBin.setFileSize(fileInfo.getFileSize());
        recycleBin.setDeleteUser(deleteUser);
        recycleBin.setExpireAt(LocalDateTime.now().plusDays(fileStorageConfig.getRecycle().getRetentionDays()));
        recycleBin = recycleBinRepository.save(recycleBin);

        String ttlKey = RECYCLE_TTL_PREFIX + recycleBin.getId();
        redisUtil.set(ttlKey, tenantCode + ":" + fileId,
                fileStorageConfig.getRecycle().getRetentionDays(), TimeUnit.DAYS);
    }

    public Page<RecycleBin> getRecycleBinList(String tenantCode, Pageable pageable) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        return recycleBinRepository.findByTenantId(tenantId, pageable);
    }

    @Transactional
    public void restoreFile(String tenantCode, Long recycleId) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        RecycleBin recycleBin = recycleBinRepository.findByTenantIdAndId(tenantId, recycleId)
                .orElseThrow(() -> new RuntimeException("回收站记录不存在"));

        FileInfo fileInfo = fileInfoRepository.findById(recycleBin.getFileId())
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        fileInfo.setIsDeleted(0);
        fileInfoRepository.save(fileInfo);

        recycleBinRepository.delete(recycleBin);

        redisUtil.delete(RECYCLE_TTL_PREFIX + recycleId);
    }

    @Transactional
    public void permanentlyDelete(String tenantCode, Long recycleId) {
        Long tenantId = tenantService.getTenantByCode(tenantCode).getId();
        RecycleBin recycleBin = recycleBinRepository.findByTenantIdAndId(tenantId, recycleId)
                .orElseThrow(() -> new RuntimeException("回收站记录不存在"));

        fileService.permanentlyDeleteFile(tenantCode, recycleBin.getFileId());
        recycleBinRepository.delete(recycleBin);

        redisUtil.delete(RECYCLE_TTL_PREFIX + recycleId);
    }

    @Transactional
    public void cleanupExpiredByTTL() {
        log.info("开始检查Redis TTL过期的回收站文件");
        LocalDateTime now = LocalDateTime.now();
        var expiredFiles = recycleBinRepository.findByExpiredAtBefore(now);

        int cleanedCount = 0;
        for (RecycleBin recycleBin : expiredFiles) {
            try {
                String ttlKey = RECYCLE_TTL_PREFIX + recycleBin.getId();
                if (!redisUtil.hasKey(ttlKey)) {
                    Optional<FileInfo> fileInfoOpt = fileInfoRepository.findById(recycleBin.getFileId());
                    if (fileInfoOpt.isPresent()) {
                        FileInfo fileInfo = fileInfoOpt.get();
                        String tenantCode = tenantService.getTenantByCode(recycleBin.getTenantId().toString()).getTenantCode();
                        fileService.permanentlyDeleteFile(tenantCode, fileInfo.getId());
                    }
                    recycleBinRepository.delete(recycleBin);
                    cleanedCount++;
                    log.info("TTL过期自动物理删除文件: recycleId={}, fileId={}", recycleBin.getId(), recycleBin.getFileId());
                }
            } catch (Exception e) {
                log.error("TTL过期清理文件失败: {}", recycleBin.getId(), e);
            }
        }
        log.info("TTL过期清理完成，共删除文件: {}", cleanedCount);
    }

    @Transactional
    public void cleanupExpiredFiles() {
        log.info("开始清理回收站过期文件");
        LocalDateTime now = LocalDateTime.now();
        int deleted = recycleBinRepository.deleteExpiredFiles(now);
        log.info("清理完成，删除过期回收站记录: {}", deleted);
    }

    @Transactional
    public void cleanupExpiredFilesWithPhysicalDelete() {
        log.info("开始清理并物理删除回收站过期文件");
        LocalDateTime now = LocalDateTime.now();
        var expiredFiles = recycleBinRepository.findByExpiredAtBefore(now);

        for (RecycleBin recycleBin : expiredFiles) {
            try {
                Optional<FileInfo> fileInfoOpt = fileInfoRepository.findById(recycleBin.getFileId());
                if (fileInfoOpt.isPresent()) {
                    FileInfo fileInfo = fileInfoOpt.get();
                    String tenantCode = tenantService.getTenantByCode(recycleBin.getTenantId().toString()).getTenantCode();
                    fileService.permanentlyDeleteFile(tenantCode, fileInfo.getId());
                }
                recycleBinRepository.delete(recycleBin);
            } catch (Exception e) {
                log.error("清理过期文件失败: {}", recycleBin.getId(), e);
            }
        }
        log.info("清理完成");
    }
}

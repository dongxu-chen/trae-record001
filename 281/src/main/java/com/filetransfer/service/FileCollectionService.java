package com.filetransfer.service;

import com.filetransfer.dto.CreateCollectionLinkRequest;
import com.filetransfer.entity.CollectedFile;
import com.filetransfer.entity.FileCollectionLink;
import com.filetransfer.repository.CollectedFileRepository;
import com.filetransfer.repository.FileCollectionLinkRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class FileCollectionService {
    private final FileCollectionLinkRepository linkRepository;
    private final CollectedFileRepository collectedFileRepository;
    private final MinIOService minIOService;
    private final StorageQuotaService storageQuotaService;
    private final AuditLogService auditLogService;

    @Transactional
    public FileCollectionLink createLink(CreateCollectionLinkRequest request) {
        String linkCode = generateLinkCode();

        FileCollectionLink link = new FileCollectionLink();
        link.setLinkCode(linkCode);
        link.setUserId(request.getUserId());
        link.setTitle(request.getTitle());
        link.setDescription(request.getDescription());
        link.setMaxFileSize(request.getMaxFileSize());
        link.setMaxFiles(request.getMaxFiles());

        if (request.getPassword() != null && !request.getPassword().isEmpty()) {
            link.setPassword(request.getPassword());
            link.setIsPasswordProtected(true);
        }

        if (request.getExpireDays() != null && request.getExpireDays() > 0) {
            link.setExpiredAt(LocalDateTime.now().plusDays(request.getExpireDays()));
        }

        link = linkRepository.save(link);

        auditLogService.logOperation(request.getUserId(), "CREATE_COLLECTION_LINK",
                null, request.getTitle(), null, "SUCCESS", null);

        return link;
    }

    public FileCollectionLink getLinkInfo(String linkCode, String password) {
        FileCollectionLink link = linkRepository.findByLinkCode(linkCode)
                .orElseThrow(() -> new RuntimeException("收集链接不存在"));

        if (!link.getIsActive()) {
            throw new RuntimeException("收集链接已失效");
        }

        if (link.getExpiredAt() != null && LocalDateTime.now().isAfter(link.getExpiredAt())) {
            throw new RuntimeException("收集链接已过期");
        }

        if (link.getIsPasswordProtected()) {
            if (password == null || !password.equals(link.getPassword())) {
                throw new RuntimeException("密码错误");
            }
        }

        return link;
    }

    @Transactional
    public CollectedFile uploadToCollection(String linkCode, MultipartFile file,
                                         String uploaderName, String uploaderEmail,
                                         String remark) {
        FileCollectionLink link = linkRepository.findByLinkCode(linkCode)
                .orElseThrow(() -> new RuntimeException("收集链接不存在"));

        if (!link.getIsActive()) {
            throw new RuntimeException("收集链接已失效");
        }

        if (link.getExpiredAt() != null && LocalDateTime.now().isAfter(link.getExpiredAt())) {
            throw new RuntimeException("收集链接已过期");
        }

        if (link.getMaxFiles() != null && link.getTotalFiles() >= link.getMaxFiles()) {
            throw new RuntimeException("已达到最大文件数量限制");
        }

        if (link.getMaxFileSize() != null && file.getSize() > link.getMaxFileSize()) {
            throw new RuntimeException("文件大小超出限制");
        }

        if (!storageQuotaService.checkQuota(link.getUserId(), file.getSize())) {
            throw new RuntimeException("存储空间不足");
        }

        String objectName = "collected/" + linkCode + "/" + UUID.randomUUID()
                + "/" + file.getOriginalFilename();

        try {
            minIOService.uploadChunk(objectName, file.getInputStream(),
                    file.getSize(), file.getContentType());
        } catch (Exception e) {
            log.error("文件上传失败", e);
            throw new RuntimeException("文件上传失败", e);
        }

        CollectedFile collectedFile = new CollectedFile();
        collectedFile.setLinkId(link.getId());
        collectedFile.setLinkCode(linkCode);
        collectedFile.setFileName(file.getOriginalFilename());
        collectedFile.setFileSize(file.getSize());
        collectedFile.setContentType(file.getContentType());
        collectedFile.setObjectName(objectName);
        collectedFile.setUploaderName(uploaderName);
        collectedFile.setUploaderEmail(uploaderEmail);
        collectedFile.setRemark(remark);
        collectedFile = collectedFileRepository.save(collectedFile);

        link.setTotalFiles(link.getTotalFiles() + 1);
        link.setTotalSize(link.getTotalSize() + file.getSize());
        linkRepository.save(link);

        storageQuotaService.increaseUsage(link.getUserId(), file.getSize());

        auditLogService.logOperation(link.getUserId(), "COLLECT_FILE_UPLOAD",
                null, file.getOriginalFilename(), file.getSize(), "SUCCESS", null);

        return collectedFile;
    }

    public List<FileCollectionLink> getUserLinks(Long userId) {
        return linkRepository.findByUserIdAndIsActiveTrueOrderByCreatedAtDesc(userId);
    }

    public List<CollectedFile> getCollectedFiles(String linkCode, Long userId) {
        FileCollectionLink link = linkRepository.findByLinkCode(linkCode)
                .orElseThrow(() -> new RuntimeException("收集链接不存在"));

        if (!link.getUserId().equals(userId)) {
            throw new RuntimeException("无权限访问");
        }

        return collectedFileRepository.findByLinkIdOrderByCreatedAtDesc(link.getId());
    }

    @Transactional
    public void deactivateLink(String linkCode, Long userId) {
        FileCollectionLink link = linkRepository.findByLinkCode(linkCode)
                .orElseThrow(() -> new RuntimeException("收集链接不存在"));

        if (!link.getUserId().equals(userId)) {
            throw new RuntimeException("无权限操作");
        }

        link.setIsActive(false);
        linkRepository.save(link);

        auditLogService.logOperation(userId, "DEACTIVATE_COLLECTION_LINK",
                null, link.getTitle(), null, "SUCCESS", null);
    }

    private String generateLinkCode() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
    }
}

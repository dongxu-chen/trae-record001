package com.filetransfer.service;

import com.filetransfer.dto.CreateShareLinkRequest;
import com.filetransfer.entity.FileShareLink;
import com.filetransfer.repository.FileShareLinkRepository;
import com.filetransfer.repository.FileInfoRepository;
import com.filetransfer.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.InputStream;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class FileShareService {
    private final FileShareLinkRepository shareLinkRepository;
    private final FileInfoRepository fileInfoRepository;
    private final UserRepository userRepository;
    private final MinIOService minIOService;
    private final WatermarkService watermarkService;
    private final AuditLogService auditLogService;

    @Transactional
    public FileShareLink createShareLink(CreateShareLinkRequest request) {
        if (!fileInfoRepository.existsById(request.getFileId())) {
            throw new RuntimeException("文件不存在");
        }

        String shareCode = generateShareCode();

        FileShareLink shareLink = new FileShareLink();
        shareLink.setShareCode(shareCode);
        shareLink.setFileId(request.getFileId());
        shareLink.setUserId(request.getUserId());
        shareLink.setTitle(request.getTitle());
        shareLink.setEnableWatermark(request.getEnableWatermark());
        shareLink.setWatermarkText(request.getWatermarkText());
        shareLink.setEnableDownload(request.getEnableDownload());
        shareLink.setEnablePreview(request.getEnablePreview());
        shareLink.setMaxViews(request.getMaxViews());

        if (request.getPassword() != null && !request.getPassword().isEmpty()) {
            shareLink.setPassword(request.getPassword());
            shareLink.setIsPasswordProtected(true);
        }

        if (request.getExpireDays() != null && request.getExpireDays() > 0) {
            shareLink.setExpiredAt(LocalDateTime.now().plusDays(request.getExpireDays()));
        }

        shareLink = shareLinkRepository.save(shareLink);

        auditLogService.logOperation(request.getUserId(), "CREATE_SHARE_LINK",
                request.getFileId(), request.getTitle(), null, "SUCCESS", null);

        return shareLink;
    }

    public FileShareLink getShareLink(String shareCode, String password) {
        FileShareLink shareLink = shareLinkRepository.findByShareCode(shareCode)
                .orElseThrow(() -> new RuntimeException("分享链接不存在"));

        validateShareLink(shareLink, password);

        return shareLink;
    }

    @Transactional
    public InputStream previewFileWithWatermark(String shareCode, String visitorInfo,
                                                 String ipAddress, String password) {
        FileShareLink shareLink = getShareLink(shareCode, password);

        if (!shareLink.getEnablePreview()) {
            throw new RuntimeException("预览功能未开启");
        }

        shareLink.setViewCount(shareLink.getViewCount() + 1);
        shareLinkRepository.save(shareLink);

        var fileInfo = fileInfoRepository.findById(shareLink.getFileId()).orElseThrow();

        if (shareLink.getEnableWatermark() && watermarkService.isImageFile(fileInfo.getOriginalFilename())) {
            InputStream originalStream = minIOService.getObject(fileInfo.getObjectName());
            byte[] watermarkedBytes = watermarkService.addTextWatermark(
                    originalStream,
                    shareLink.getWatermarkText(),
                    visitorInfo,
                    ipAddress
            );
            if (watermarkedBytes != null) {
                return new java.io.ByteArrayInputStream(watermarkedBytes);
            }
        }

        return minIOService.getObject(fileInfo.getObjectName());
    }

    public InputStream downloadFile(String shareCode, String password) {
        FileShareLink shareLink = getShareLink(shareCode, password);

        if (!shareLink.getEnableDownload()) {
            throw new RuntimeException("下载功能未开启");
        }

        var fileInfo = fileInfoRepository.findById(shareLink.getFileId()).orElseThrow();
        return minIOService.getObject(fileInfo.getObjectName());
    }

    public List<FileShareLink> getUserShareLinks(Long userId) {
        return shareLinkRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    @Transactional
    public void deactivateShareLink(String shareCode, Long userId) {
        FileShareLink shareLink = shareLinkRepository.findByShareCode(shareCode)
                .orElseThrow(() -> new RuntimeException("分享链接不存在"));

        if (!shareLink.getUserId().equals(userId)) {
            throw new RuntimeException("无权限操作");
        }

        shareLink.setIsActive(false);
        shareLinkRepository.save(shareLink);
    }

    private void validateShareLink(FileShareLink shareLink, String password) {
        if (!shareLink.getIsActive()) {
            throw new RuntimeException("分享链接已失效");
        }

        if (shareLink.getExpiredAt() != null && LocalDateTime.now().isAfter(shareLink.getExpiredAt())) {
            throw new RuntimeException("分享链接已过期");
        }

        if (shareLink.getMaxViews() != null && shareLink.getViewCount() >= shareLink.getMaxViews()) {
            throw new RuntimeException("分享链接访问次数已达上限");
        }

        if (shareLink.getIsPasswordProtected()) {
            if (password == null || !password.equals(shareLink.getPassword())) {
                throw new RuntimeException("密码错误");
            }
        }
    }

    private String generateShareCode() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 12).toUpperCase();
    }
}

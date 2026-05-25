package com.filetransfer.service;

import com.filetransfer.dto.CreateDistributionRequest;
import com.filetransfer.dto.DistributionDetailDTO;
import com.filetransfer.entity.DistributionFile;
import com.filetransfer.entity.DistributionRecipient;
import com.filetransfer.entity.FileDistribution;
import com.filetransfer.entity.FileInfo;
import com.filetransfer.entity.User;
import com.filetransfer.repository.DistributionFileRepository;
import com.filetransfer.repository.DistributionRecipientRepository;
import com.filetransfer.repository.FileDistributionRepository;
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
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class FileDistributionService {
    private final FileDistributionRepository distributionRepository;
    private final DistributionFileRepository distributionFileRepository;
    private final DistributionRecipientRepository distributionRecipientRepository;
    private final FileInfoRepository fileInfoRepository;
    private final UserRepository userRepository;
    private final MinIOService minIOService;
    private final AuditLogService auditLogService;

    @Transactional
    public FileDistribution createDistribution(CreateDistributionRequest request) {
        User sourceUser = userRepository.findById(request.getUserId())
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        String distributionId = generateDistributionId();

        List<FileInfo> fileInfos = fileInfoRepository.findAllById(request.getFileIds());
        if (fileInfos.isEmpty()) {
            throw new RuntimeException("文件不存在");
        }

        long totalSize = fileInfos.stream().mapToLong(FileInfo::getFileSize).sum();

        FileDistribution distribution = new FileDistribution();
        distribution.setDistributionId(distributionId);
        distribution.setSourceUserId(request.getUserId());
        distribution.setSourceUsername(sourceUser.getUsername());
        distribution.setTitle(request.getTitle() != null ? request.getTitle() : "文件分发");
        distribution.setMessage(request.getMessage());
        distribution.setTotalFiles(fileInfos.size());
        distribution.setTotalSize(totalSize);
        distribution.setTotalRecipients(request.getRecipients() != null ? request.getRecipients().size() : 0);

        if (request.getExpireDays() != null && request.getExpireDays() > 0) {
            distribution.setExpiredAt(LocalDateTime.now().plusDays(request.getExpireDays()));
        }

        distribution = distributionRepository.save(distribution);

        for (FileInfo fileInfo : fileInfos) {
            DistributionFile df = new DistributionFile();
            df.setDistributionId(distributionId);
            df.setFileId(fileInfo.getId());
            df.setFileName(fileInfo.getOriginalFilename());
            df.setFileSize(fileInfo.getFileSize());
            df.setContentType(fileInfo.getContentType());
            df.setObjectName(fileInfo.getObjectName());
            distributionFileRepository.save(df);
        }

        if (request.getRecipients() != null) {
            for (CreateDistributionRequest.RecipientDTO r : request.getRecipients()) {
                DistributionRecipient recipient = new DistributionRecipient();
                recipient.setDistributionId(distributionId);
                recipient.setRecipientType(r.getType() != null ? r.getType() : "USER");
                recipient.setRecipientIdentifier(r.getIdentifier());
                recipient.setRecipientName(r.getName());
                distributionRecipientRepository.save(recipient);
            }
        }

        auditLogService.logOperation(request.getUserId(), "CREATE_DISTRIBUTION",
                null, distribution.getTitle(), totalSize, "SUCCESS",
                "文件数: " + fileInfos.size() + ", 收件人: " + distribution.getTotalRecipients());

        log.info("创建文件分发: {}, 文件数: {}, 收件人: {}",
                distributionId, fileInfos.size(), distribution.getTotalRecipients());

        return distribution;
    }

    public DistributionDetailDTO getDistributionDetail(String distributionId, String recipientIdentifier) {
        FileDistribution distribution = distributionRepository.findByDistributionId(distributionId)
                .orElseThrow(() -> new RuntimeException("分发不存在"));

        validateDistribution(distribution);

        if (recipientIdentifier != null && !recipientIdentifier.isEmpty()) {
            DistributionRecipient recipient = distributionRecipientRepository
                    .findByDistributionIdAndRecipientTypeAndRecipientIdentifier(
                            distributionId, "USER", recipientIdentifier)
                    .orElse(null);
            if (recipient != null && !recipient.getHasViewed()) {
                recipient.setHasViewed(true);
                recipient.setViewedAt(LocalDateTime.now());
                distributionRecipientRepository.save(recipient);

                distribution.setViewCount(distribution.getViewCount() + 1);
                distributionRepository.save(distribution);
            }
        }

        List<DistributionFile> files = distributionFileRepository.findByDistributionIdOrderByCreatedAtDesc(distributionId);
        List<DistributionRecipient> recipients = distributionRecipientRepository.findByDistributionId(distributionId);

        return DistributionDetailDTO.builder()
                .distributionId(distribution.getDistributionId())
                .title(distribution.getTitle())
                .message(distribution.getMessage())
                .sourceUsername(distribution.getSourceUsername())
                .totalFiles(distribution.getTotalFiles())
                .totalSize(distribution.getTotalSize())
                .totalRecipients(distribution.getTotalRecipients())
                .viewCount(distribution.getViewCount())
                .downloadCount(distribution.getDownloadCount())
                .createdAt(distribution.getCreatedAt())
                .expiredAt(distribution.getExpiredAt())
                .isActive(distribution.getIsActive())
                .files(files.stream().map(f -> DistributionDetailDTO.DistributionFileDTO.builder()
                        .fileId(f.getFileId())
                        .fileName(f.getFileName())
                        .fileSize(f.getFileSize())
                        .contentType(f.getContentType())
                        .viewCount(f.getViewCount())
                        .downloadCount(f.getDownloadCount())
                        .build()).collect(Collectors.toList()))
                .recipients(recipients.stream().map(r -> DistributionDetailDTO.DistributionRecipientDTO.builder()
                        .type(r.getRecipientType())
                        .identifier(r.getRecipientIdentifier())
                        .name(r.getRecipientName())
                        .hasViewed(r.getHasViewed())
                        .hasDownloaded(r.getHasDownloaded())
                        .viewedAt(r.getViewedAt())
                        .downloadedAt(r.getDownloadedAt())
                        .build()).collect(Collectors.toList()))
                .build();
    }

    public InputStream downloadDistributionFile(String distributionId, Long fileId, String recipientIdentifier) {
        FileDistribution distribution = distributionRepository.findByDistributionId(distributionId)
                .orElseThrow(() -> new RuntimeException("分发不存在"));

        validateDistribution(distribution);

        DistributionFile distributionFile = distributionFileRepository.findByDistributionIdOrderByCreatedAtDesc(distributionId)
                .stream().filter(f -> f.getFileId().equals(fileId)).findFirst()
                .orElseThrow(() -> new RuntimeException("文件不在此分发中"));

        if (recipientIdentifier != null && !recipientIdentifier.isEmpty()) {
            DistributionRecipient recipient = distributionRecipientRepository
                    .findByDistributionIdAndRecipientTypeAndRecipientIdentifier(
                            distributionId, "USER", recipientIdentifier)
                    .orElse(null);
            if (recipient != null && !recipient.getHasDownloaded()) {
                recipient.setHasDownloaded(true);
                recipient.setDownloadedAt(LocalDateTime.now());
                distributionRecipientRepository.save(recipient);
            }
        }

        distributionFile.setDownloadCount(distributionFile.getDownloadCount() + 1);
        distributionFileRepository.save(distributionFile);

        distribution.setDownloadCount(distribution.getDownloadCount() + 1);
        distributionRepository.save(distribution);

        return minIOService.getObject(distributionFile.getObjectName());
    }

    public List<FileDistribution> getUserDistributions(Long userId) {
        return distributionRepository.findBySourceUserIdOrderByCreatedAtDesc(userId);
    }

    @Transactional
    public void cancelDistribution(String distributionId, Long userId) {
        FileDistribution distribution = distributionRepository.findByDistributionId(distributionId)
                .orElseThrow(() -> new RuntimeException("分发不存在"));

        if (!distribution.getSourceUserId().equals(userId)) {
            throw new RuntimeException("无权限操作");
        }

        distribution.setIsActive(false);
        distributionRepository.save(distribution);

        auditLogService.logOperation(userId, "CANCEL_DISTRIBUTION",
                null, distribution.getTitle(), null, "SUCCESS", null);
    }

    private void validateDistribution(FileDistribution distribution) {
        if (!distribution.getIsActive()) {
            throw new RuntimeException("分发已取消");
        }

        if (distribution.getExpiredAt() != null && LocalDateTime.now().isAfter(distribution.getExpiredAt())) {
            throw new RuntimeException("分发已过期");
        }
    }

    private String generateDistributionId() {
        return "DIST-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();
    }
}

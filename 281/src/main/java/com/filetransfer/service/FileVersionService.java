package com.filetransfer.service;

import com.filetransfer.dto.FileConflictDTO;
import com.filetransfer.dto.FileVersionDTO;
import com.filetransfer.entity.FileInfo;
import com.filetransfer.entity.FileVersion;
import com.filetransfer.entity.User;
import com.filetransfer.repository.FileInfoRepository;
import com.filetransfer.repository.FileVersionRepository;
import com.filetransfer.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class FileVersionService {
    private final FileVersionRepository fileVersionRepository;
    private final FileInfoRepository fileInfoRepository;
    private final UserRepository userRepository;
    private final MinIOService minIOService;

    public FileConflictDTO checkConflict(String fileName, String fileMd5, Long fileSize, Long userId) {
        List<FileInfo> userFiles = fileInfoRepository.findByUserIdAndIsDeletedFalse(userId);

        for (FileInfo file : userFiles) {
            if (file.getOriginalFilename().equals(fileName)) {
                if (file.getFileMd5() != null && file.getFileMd5().equals(fileMd5)
                        && file.getFileSize().equals(fileSize)) {
                    return FileConflictDTO.builder()
                            .hasConflict(true)
                            .conflictType("IDENTICAL")
                            .existingFileId(file.getId())
                            .existingFileName(file.getOriginalFilename())
                            .existingFileMd5(file.getFileMd5())
                            .existingFileSize(file.getFileSize())
                            .existingCreatedAt(file.getCreatedAt())
                            .suggestedAction("SKIP")
                            .message("检测到完全相同的文件，建议跳过上传")
                            .build();
                }

                FileVersion currentVersion = fileVersionRepository.findByFileIdAndIsCurrentTrue(file.getId()).orElse(null);

                return FileConflictDTO.builder()
                        .hasConflict(true)
                        .conflictType("VERSION")
                        .existingFileId(file.getId())
                        .existingFileName(file.getOriginalFilename())
                        .existingFileMd5(file.getFileMd5())
                        .existingFileSize(file.getFileSize())
                        .existingVersion(currentVersion != null ? currentVersion.getVersionNumber() : 1)
                        .existingCreatedAt(file.getCreatedAt())
                        .suggestedAction("ASK")
                        .message("检测到同名文件，可选择创建新版本或覆盖")
                        .build();
            }
        }

        if (fileMd5 != null) {
            FileInfo existingByMd5 = fileInfoRepository.findByFileMd5AndFileSize(fileMd5, fileSize).orElse(null);
            if (existingByMd5 != null && !existingByMd5.getUserId().equals(userId)) {
                User uploader = userRepository.findById(existingByMd5.getUserId()).orElse(null);
                return FileConflictDTO.builder()
                        .hasConflict(true)
                        .conflictType("OTHER_USER")
                        .existingFileId(existingByMd5.getId())
                        .existingFileName(existingByMd5.getOriginalFilename())
                        .existingFileMd5(fileMd5)
                        .existingFileSize(fileSize)
                        .existingUsername(uploader != null ? uploader.getUsername() : "unknown")
                        .existingCreatedAt(existingByMd5.getCreatedAt())
                        .suggestedAction("ASK")
                        .message("其他用户已上传相同内容的文件")
                        .build();
            }
        }

        return FileConflictDTO.builder()
                .hasConflict(false)
                .suggestedAction("UPLOAD")
                .message("无冲突，可以上传")
                .build();
    }

    @Transactional
    public FileVersion createNewVersion(Long fileId, String newObjectId, String fileMd5,
                                        Long fileSize, Long userId, String changeDescription) {
        FileInfo fileInfo = fileInfoRepository.findById(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        FileVersion oldVersion = fileVersionRepository.findByFileIdAndIsCurrentTrue(fileId).orElse(null);
        if (oldVersion != null) {
            oldVersion.setIsCurrent(false);
            fileVersionRepository.save(oldVersion);
        }

        int versionCount = fileVersionRepository.countByFileId(fileId);

        User user = userRepository.findById(userId).orElse(null);

        FileVersion newVersion = new FileVersion();
        newVersion.setFileId(fileId);
        newVersion.setFileMd5(fileMd5);
        newVersion.setVersionNumber(versionCount + 1);
        newVersion.setUserId(userId);
        newVersion.setUsername(user != null ? user.getUsername() : "unknown");
        newVersion.setObjectName(newObjectId);
        newVersion.setFileSize(fileSize);
        newVersion.setChangeDescription(changeDescription);
        newVersion.setIsCurrent(true);

        fileVersionRepository.save(newVersion);

        fileInfo.setObjectName(newObjectId);
        fileInfo.setFileMd5(fileMd5);
        fileInfo.setFileSize(fileSize);
        fileInfoRepository.save(fileInfo);

        log.info("文件 {} 创建新版本: v{}", fileId, versionCount + 1);
        return newVersion;
    }

    public List<FileVersionDTO> getFileVersions(Long fileId) {
        List<FileVersion> versions = fileVersionRepository.findByFileIdOrderByVersionNumberDesc(fileId);
        return versions.stream().map(v -> {
            String url = minIOService.getPresignedUrl(v.getObjectName(), 1, TimeUnit.HOURS);
            return FileVersionDTO.builder()
                    .id(v.getId())
                    .fileId(v.getFileId())
                    .versionNumber(v.getVersionNumber())
                    .fileMd5(v.getFileMd5())
                    .userId(v.getUserId())
                    .username(v.getUsername())
                    .fileSize(v.getFileSize())
                    .changeDescription(v.getChangeDescription())
                    .isCurrent(v.getIsCurrent())
                    .createdAt(v.getCreatedAt())
                    .downloadUrl(url)
                    .build();
        }).collect(Collectors.toList());
    }

    @Transactional
    public void restoreVersion(Long fileId, Integer versionNumber, Long userId) {
        FileVersion targetVersion = fileVersionRepository.findByFileIdAndVersionNumber(fileId, versionNumber)
                .orElseThrow(() -> new RuntimeException("版本不存在"));

        FileVersion currentVersion = fileVersionRepository.findByFileIdAndIsCurrentTrue(fileId).orElse(null);
        if (currentVersion != null) {
            currentVersion.setIsCurrent(false);
            fileVersionRepository.save(currentVersion);
        }

        targetVersion.setIsCurrent(true);
        fileVersionRepository.save(targetVersion);

        FileInfo fileInfo = fileInfoRepository.findById(fileId).orElseThrow();
        fileInfo.setObjectName(targetVersion.getObjectName());
        fileInfo.setFileMd5(targetVersion.getFileMd5());
        fileInfo.setFileSize(targetVersion.getFileSize());
        fileInfoRepository.save(fileInfo);

        log.info("文件 {} 恢复到版本 v{}", fileId, versionNumber);
    }
}

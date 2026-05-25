package com.filetransfer.service;

import com.filetransfer.dto.ArchiveEntryDTO;
import com.filetransfer.entity.FileInfo;
import com.filetransfer.repository.FileInfoRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.compress.archivers.ArchiveEntry;
import org.apache.commons.compress.archivers.ArchiveInputStream;
import org.apache.commons.compress.archivers.zip.ZipArchiveInputStream;
import org.apache.commons.compress.utils.IOUtils;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ArchivePreviewService {
    private final FileInfoRepository fileInfoRepository;
    private final MinIOService minIOService;

    public boolean isArchiveFile(String fileName) {
        String lowerName = fileName.toLowerCase();
        return lowerName.endsWith(".zip") || lowerName.endsWith(".jar")
                || lowerName.endsWith(".war") || lowerName.endsWith(".ear");
    }

    public List<ArchiveEntryDTO> listArchiveContents(Long fileId) {
        FileInfo fileInfo = fileInfoRepository.findByIdAndIsDeletedFalse(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        if (!isArchiveFile(fileInfo.getOriginalFilename())) {
            throw new RuntimeException("不支持的压缩包格式");
        }

        List<ArchiveEntryDTO> entries = new ArrayList<>();

        try (InputStream is = minIOService.getObject(fileInfo.getObjectName());
             ArchiveInputStream ais = new ZipArchiveInputStream(is, StandardCharsets.UTF_8.name())) {

            ArchiveEntry entry;
            while ((entry = ais.getNextEntry()) != null) {
                ArchiveEntryDTO dto = ArchiveEntryDTO.builder()
                        .name(getEntryName(entry.getName()))
                        .path(entry.getName())
                        .size(entry.getSize())
                        .isDirectory(entry.isDirectory())
                        .level(calculateLevel(entry.getName()))
                        .build();

                if (entry.getLastModifiedDate() != null) {
                    dto.setLastModified(LocalDateTime.ofInstant(
                            entry.getLastModifiedDate().toInstant(),
                            ZoneId.systemDefault()).toString());
                }

                entries.add(dto);
            }

            entries.sort(Comparator
                    .comparing(ArchiveEntryDTO::getIsDirectory, Comparator.reverseOrder())
                    .thenComparing(ArchiveEntryDTO::getPath));

        } catch (Exception e) {
            log.error("读取压缩包内容失败", e);
            throw new RuntimeException("读取压缩包内容失败", e);
        }

        return entries;
    }

    public byte[] previewFileInArchive(Long fileId, String entryPath) {
        FileInfo fileInfo = fileInfoRepository.findByIdAndIsDeletedFalse(fileId)
                .orElseThrow(() -> new RuntimeException("文件不存在"));

        if (!isArchiveFile(fileInfo.getOriginalFilename())) {
            throw new RuntimeException("不支持的压缩包格式");
        }

        try (InputStream is = minIOService.getObject(fileInfo.getObjectName());
             ArchiveInputStream ais = new ZipArchiveInputStream(is, StandardCharsets.UTF_8.name())) {

            ArchiveEntry entry;
            while ((entry = ais.getNextEntry()) != null) {
                if (entry.getName().equals(entryPath) && !entry.isDirectory()) {
                    if (entry.getSize() > 10 * 1024 * 1024) {
                        throw new RuntimeException("文件过大，无法预览");
                    }

                    ByteArrayOutputStream baos = new ByteArrayOutputStream();
                    IOUtils.copy(ais, baos);
                    return baos.toByteArray();
                }
            }

            throw new RuntimeException("文件在压缩包中不存在");

        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            log.error("预览压缩包内文件失败", e);
            throw new RuntimeException("预览压缩包内文件失败", e);
        }
    }

    private String getEntryName(String path) {
        if (path.endsWith("/")) {
            path = path.substring(0, path.length() - 1);
        }
        int lastSlash = path.lastIndexOf("/");
        return lastSlash >= 0 ? path.substring(lastSlash + 1) : path;
    }

    private int calculateLevel(String path) {
        int count = 0;
        for (char c : path.toCharArray()) {
            if (c == '/') {
                count++;
            }
        }
        return path.endsWith("/") ? count - 1 : count;
    }
}

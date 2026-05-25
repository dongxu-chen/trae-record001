package com.filetransfer.service;

import com.filetransfer.dto.ChunkUploadRequest;
import com.filetransfer.dto.ProgressMessage;
import com.filetransfer.dto.UploadInitRequest;
import com.filetransfer.dto.UploadInitResponse;
import com.filetransfer.entity.ChunkUploadTask;
import com.filetransfer.entity.FileInfo;
import com.filetransfer.entity.UploadedChunk;
import com.filetransfer.repository.ChunkUploadTaskRepository;
import com.filetransfer.repository.FileInfoRepository;
import com.filetransfer.repository.UploadedChunkRepository;
import com.filetransfer.util.ChunkOrderManager;
import com.filetransfer.websocket.ProgressWebSocketHandler;
import io.minio.messages.ComposeSource;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class FileUploadService {
    private final ChunkUploadTaskRepository chunkUploadTaskRepository;
    private final UploadedChunkRepository uploadedChunkRepository;
    private final FileInfoRepository fileInfoRepository;
    private final MinIOService minIOService;
    private final AuditLogService auditLogService;
    private final StorageQuotaService storageQuotaService;
    private final ProgressWebSocketHandler progressWebSocketHandler;
    private final ChunkOrderManager chunkOrderManager;

    @Value("${file.chunk-size:5242880}")
    private Long defaultChunkSize;

    @Transactional
    public UploadInitResponse initUpload(UploadInitRequest request) {
        log.info("初始化上传: fileName={}, fileSize={}", request.getFileName(), request.getFileSize());

        if (request.getFileMd5() != null && !request.getFileMd5().isEmpty() && request.getFileSize() != null) {
            FileInfo existingFile = fileInfoRepository.findByFileMd5AndFileSize(
                    request.getFileMd5(), request.getFileSize()).orElse(null);
            if (existingFile != null) {
                log.info("秒传命中: fileMd5={}, fileSize={}", request.getFileMd5(), request.getFileSize());
                String fileUrl = minIOService.getPresignedUrl(existingFile.getObjectName(), 1, TimeUnit.HOURS);
                return UploadInitResponse.builder()
                        .rapidUpload(true)
                        .fileId(existingFile.getId())
                        .fileUrl(fileUrl)
                        .fileName(existingFile.getOriginalFilename())
                        .fileSize(existingFile.getFileSize())
                        .build();
            }
        }

        if (!storageQuotaService.checkQuota(request.getUserId(), request.getFileSize())) {
            throw new RuntimeException("存储空间不足");
        }

        int totalChunks = (int) Math.ceil((double) request.getFileSize() / defaultChunkSize);

        String uploadId = UUID.randomUUID().toString().replace("-", "");

        ChunkUploadTask task = new ChunkUploadTask();
        task.setUploadId(uploadId);
        task.setUserId(request.getUserId());
        task.setFileName(request.getFileName());
        task.setFileSize(request.getFileSize());
        task.setFileMd5(request.getFileMd5());
        task.setChunkSize(defaultChunkSize);
        task.setTotalChunks(totalChunks);
        task.setContentType(request.getContentType());
        task.setStatus("UPLOADING");
        task.setExpiredAt(LocalDateTime.now().plusHours(24));
        chunkUploadTaskRepository.save(task);

        List<Integer> uploadedChunks = new ArrayList<>();

        auditLogService.logOperation(request.getUserId(), "INIT_UPLOAD", null,
                request.getFileName(), request.getFileSize(), "SUCCESS", null);

        return UploadInitResponse.builder()
                .uploadId(uploadId)
                .fileName(request.getFileName())
                .fileSize(request.getFileSize())
                .totalChunks(totalChunks)
                .chunkSize(defaultChunkSize)
                .uploadedChunks(uploadedChunks)
                .needMerge(true)
                .rapidUpload(false)
                .build();
    }

    @Transactional
    public String uploadChunk(String uploadId, ChunkUploadRequest request, MultipartFile file) {
        ChunkUploadTask task = chunkUploadTaskRepository.findByUploadId(uploadId)
                .orElseThrow(() -> new RuntimeException("上传任务不存在"));

        if (!"UPLOADING".equals(task.getStatus())) {
            throw new RuntimeException("上传任务已完成或已取消");
        }

        ChunkOrderManager.ChunkCheckResult orderResult = chunkOrderManager.checkChunkOrder(
                uploadId, request.getChunkNumber(), task.getTotalChunks());

        if (!orderResult.canProcess()) {
            if (orderResult.isDuplicate()) {
                return "分片已上传";
            }
            throw new RuntimeException(orderResult.getMessage());
        }

        if (uploadedChunkRepository.existsByUploadIdAndChunkNumber(uploadId, request.getChunkNumber())) {
            return "分片已上传";
        }

        String chunkObjectName = "chunks/" + uploadId + "/" + request.getChunkNumber();
        try {
            minIOService.uploadChunk(chunkObjectName, file.getInputStream(),
                    file.getSize(), request.getContentType());
        } catch (Exception e) {
            log.error("分片上传失败", e);
            throw new RuntimeException("分片上传失败", e);
        }

        UploadedChunk chunk = new UploadedChunk();
        chunk.setUploadId(uploadId);
        chunk.setChunkNumber(request.getChunkNumber());
        chunk.setChunkSize(file.getSize());
        chunk.setObjectName(chunkObjectName);
        uploadedChunkRepository.save(chunk);

        long uploadedCount = uploadedChunkRepository.countByUploadId(uploadId);
        task.setUploadedChunks((int) uploadedCount);
        chunkUploadTaskRepository.save(task);

        sendProgress(task, request.getChunkNumber());

        if (orderResult.isOutOfOrder()) {
            return "乱序分片已接收并缓存";
        }
        return "分片上传成功";
    }

    private void sendProgress(ChunkUploadTask task, int currentChunk) {
        double progress = (double) task.getUploadedChunks() / task.getTotalChunks() * 100;
        long uploadedSize = (long) task.getUploadedChunks() * task.getChunkSize();

        ProgressMessage message = ProgressMessage.builder()
                .uploadId(task.getUploadId())
                .fileName(task.getFileName())
                .fileSize(task.getFileSize())
                .uploadedSize(Math.min(uploadedSize, task.getFileSize()))
                .totalChunks(task.getTotalChunks())
                .uploadedChunks(task.getUploadedChunks())
                .currentChunk(currentChunk)
                .progress(Math.round(progress * 100.0) / 100.0)
                .status("UPLOADING")
                .build();

        progressWebSocketHandler.sendProgress(task.getUploadId(), message);
    }

    @Transactional
    public FileInfo mergeChunks(String uploadId) {
        log.info("开始合并分片: uploadId={}", uploadId);

        ChunkUploadTask task = chunkUploadTaskRepository.findByUploadId(uploadId)
                .orElseThrow(() -> new RuntimeException("上传任务不存在"));

        ProgressMessage mergingMessage = ProgressMessage.builder()
                .uploadId(uploadId)
                .fileName(task.getFileName())
                .fileSize(task.getFileSize())
                .uploadedSize(task.getFileSize())
                .totalChunks(task.getTotalChunks())
                .uploadedChunks(task.getTotalChunks())
                .progress(95.0)
                .status("MERGING")
                .message("正在合并分片...")
                .build();
        progressWebSocketHandler.sendProgress(uploadId, mergingMessage);

        List<UploadedChunk> chunks = uploadedChunkRepository.findByUploadIdOrderByChunkNumberAsc(uploadId);
        if (chunks.size() != task.getTotalChunks()) {
            throw new RuntimeException("分片不完整，无法合并");
        }

        String finalObjectName = "files/" + UUID.randomUUID().toString().replace("-", "")
                + "/" + task.getFileName();

        List<ComposeSource> sources = chunks.stream()
                .map(chunk -> ComposeSource.builder()
                        .object(chunk.getObjectName())
                        .build())
                .collect(Collectors.toList());

        try {
            minIOService.composeObject(finalObjectName, sources);
        } catch (Exception e) {
            log.error("合并分片失败", e);
            throw new RuntimeException("合并分片失败", e);
        }

        FileInfo fileInfo = new FileInfo();
        fileInfo.setUserId(task.getUserId());
        fileInfo.setFileName(task.getFileName());
        fileInfo.setOriginalFilename(task.getFileName());
        fileInfo.setFileSize(task.getFileSize());
        fileInfo.setFileMd5(task.getFileMd5());
        fileInfo.setContentType(task.getContentType());
        fileInfo.setObjectName(finalObjectName);
        fileInfo.setIsCompressed(false);
        fileInfo = fileInfoRepository.save(fileInfo);

        storageQuotaService.increaseUsage(task.getUserId(), task.getFileSize());

        for (UploadedChunk chunk : chunks) {
            minIOService.deleteObject(chunk.getObjectName());
        }
        uploadedChunkRepository.deleteByUploadId(uploadId);
        chunkUploadTaskRepository.deleteByUploadId(uploadId);
        chunkOrderManager.removeUploadState(uploadId);

        ProgressMessage completeMessage = ProgressMessage.builder()
                .uploadId(uploadId)
                .fileName(task.getFileName())
                .fileSize(task.getFileSize())
                .uploadedSize(task.getFileSize())
                .totalChunks(task.getTotalChunks())
                .uploadedChunks(task.getTotalChunks())
                .progress(100.0)
                .status("COMPLETE")
                .message("上传完成")
                .fileId(fileInfo.getId())
                .build();
        progressWebSocketHandler.sendProgress(uploadId, completeMessage);

        auditLogService.logOperation(task.getUserId(), "UPLOAD_COMPLETE", fileInfo.getId(),
                fileInfo.getOriginalFilename(), fileInfo.getFileSize(), "SUCCESS", null);

        log.info("文件合并完成: fileId={}, objectName={}", fileInfo.getId(), finalObjectName);
        return fileInfo;
    }

    public List<Integer> getUploadedChunks(String uploadId) {
        List<UploadedChunk> chunks = uploadedChunkRepository.findByUploadIdOrderByChunkNumberAsc(uploadId);
        return chunks.stream()
                .map(UploadedChunk::getChunkNumber)
                .collect(Collectors.toList());
    }
}

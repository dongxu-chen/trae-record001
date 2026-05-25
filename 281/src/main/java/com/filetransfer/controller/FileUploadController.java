package com.filetransfer.controller;

import com.filetransfer.common.Result;
import com.filetransfer.dto.ChunkUploadRequest;
import com.filetransfer.dto.UploadInitRequest;
import com.filetransfer.dto.UploadInitResponse;
import com.filetransfer.entity.FileInfo;
import com.filetransfer.service.FileUploadService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.concurrent.TimeUnit;

@RestController
@RequestMapping("/upload")
@RequiredArgsConstructor
public class FileUploadController {
    private final FileUploadService fileUploadService;

    @PostMapping("/init")
    public Result<UploadInitResponse> initUpload(@Valid @RequestBody UploadInitRequest request) {
        UploadInitResponse response = fileUploadService.initUpload(request);
        return Result.success(response);
    }

    @PostMapping("/chunk/{uploadId}")
    public Result<String> uploadChunk(
            @PathVariable String uploadId,
            @Valid ChunkUploadRequest request,
            @RequestParam("file") MultipartFile file) {
        String message = fileUploadService.uploadChunk(uploadId, request, file);
        return Result.success(message);
    }

    @PostMapping("/merge/{uploadId}")
    public Result<FileInfo> mergeChunks(@PathVariable String uploadId) {
        FileInfo fileInfo = fileUploadService.mergeChunks(uploadId);
        return Result.success(fileInfo);
    }

    @GetMapping("/chunks/{uploadId}")
    public Result<List<Integer>> getUploadedChunks(@PathVariable String uploadId) {
        List<Integer> uploadedChunks = fileUploadService.getUploadedChunks(uploadId);
        return Result.success(uploadedChunks);
    }
}

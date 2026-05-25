package com.filetransfer.controller;

import com.filetransfer.common.Result;
import com.filetransfer.dto.ArchiveEntryDTO;
import com.filetransfer.service.ArchivePreviewService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

@RestController
@RequestMapping("/archive")
@RequiredArgsConstructor
public class ArchivePreviewController {
    private final ArchivePreviewService archivePreviewService;

    @GetMapping("/list/{fileId}")
    public Result<List<ArchiveEntryDTO>> listArchiveContents(@PathVariable Long fileId) {
        List<ArchiveEntryDTO> entries = archivePreviewService.listArchiveContents(fileId);
        return Result.success(entries);
    }

    @GetMapping("/preview/{fileId}")
    public ResponseEntity<byte[]> previewFile(
            @PathVariable Long fileId,
            @RequestParam String path) {
        byte[] content = archivePreviewService.previewFileInArchive(fileId, path);

        String fileName = path;
        int lastSlash = path.lastIndexOf("/");
        if (lastSlash >= 0) {
            fileName = path.substring(lastSlash + 1);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        headers.setContentDispositionFormData("inline",
                URLEncoder.encode(fileName, StandardCharsets.UTF_8));

        return ResponseEntity.ok()
                .headers(headers)
                .body(content);
    }

    @GetMapping("/download/{fileId}")
    public ResponseEntity<byte[]> downloadFile(
            @PathVariable Long fileId,
            @RequestParam String path) {
        byte[] content = archivePreviewService.previewFileInArchive(fileId, path);

        String fileName = path;
        int lastSlash = path.lastIndexOf("/");
        if (lastSlash >= 0) {
            fileName = path.substring(lastSlash + 1);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        headers.setContentDispositionFormData("attachment",
                URLEncoder.encode(fileName, StandardCharsets.UTF_8));

        return ResponseEntity.ok()
                .headers(headers)
                .body(content);
    }
}

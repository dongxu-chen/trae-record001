package com.filetransfer.controller;

import com.filetransfer.common.Result;
import com.filetransfer.dto.CreateCollectionLinkRequest;
import com.filetransfer.entity.CollectedFile;
import com.filetransfer.entity.FileCollectionLink;
import com.filetransfer.service.FileCollectionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/collection")
@RequiredArgsConstructor
public class FileCollectionController {
    private final FileCollectionService fileCollectionService;

    @PostMapping("/create")
    public Result<FileCollectionLink> createLink(@Valid @RequestBody CreateCollectionLinkRequest request) {
        FileCollectionLink link = fileCollectionService.createLink(request);
        return Result.success(link);
    }

    @GetMapping("/info/{linkCode}")
    public Result<FileCollectionLink> getLinkInfo(
            @PathVariable String linkCode,
            @RequestParam(required = false) String password) {
        FileCollectionLink link = fileCollectionService.getLinkInfo(linkCode, password);
        return Result.success(link);
    }

    @PostMapping("/upload")
    public Result<CollectedFile> uploadToCollection(
            @RequestParam String linkCode,
            @RequestParam("file") MultipartFile file,
            @RequestParam(required = false) String uploaderName,
            @RequestParam(required = false) String uploaderEmail,
            @RequestParam(required = false) String remark) {
        CollectedFile collectedFile = fileCollectionService.uploadToCollection(
                linkCode, file, uploaderName, uploaderEmail, remark);
        return Result.success(collectedFile);
    }

    @GetMapping("/user/list")
    public Result<List<FileCollectionLink>> getUserLinks(
            @RequestParam(defaultValue = "1") Long userId) {
        List<FileCollectionLink> links = fileCollectionService.getUserLinks(userId);
        return Result.success(links);
    }

    @GetMapping("/files/{linkCode}")
    public Result<List<CollectedFile>> getCollectedFiles(
            @PathVariable String linkCode,
            @RequestParam(defaultValue = "1") Long userId) {
        List<CollectedFile> files = fileCollectionService.getCollectedFiles(linkCode, userId);
        return Result.success(files);
    }

    @PostMapping("/deactivate/{linkCode}")
    public Result<Void> deactivateLink(
            @PathVariable String linkCode,
            @RequestParam(defaultValue = "1") Long userId) {
        fileCollectionService.deactivateLink(linkCode, userId);
        return Result.success();
    }
}

package com.filetransfer.controller;

import com.filetransfer.common.Result;
import com.filetransfer.dto.FileConflictDTO;
import com.filetransfer.dto.FileVersionDTO;
import com.filetransfer.entity.FileVersion;
import com.filetransfer.service.FileVersionService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/versions")
@RequiredArgsConstructor
public class FileVersionController {
    private final FileVersionService fileVersionService;

    @GetMapping("/check")
    public Result<FileConflictDTO> checkConflict(
            @RequestParam String fileName,
            @RequestParam(required = false) String fileMd5,
            @RequestParam Long fileSize,
            @RequestParam(defaultValue = "1") Long userId) {
        FileConflictDTO conflict = fileVersionService.checkConflict(fileName, fileMd5, fileSize, userId);
        return Result.success(conflict);
    }

    @GetMapping("/file/{fileId}")
    public Result<List<FileVersionDTO>> getFileVersions(@PathVariable Long fileId) {
        List<FileVersionDTO> versions = fileVersionService.getFileVersions(fileId);
        return Result.success(versions);
    }

    @PostMapping("/restore/{fileId}/{versionNumber}")
    public Result<Void> restoreVersion(
            @PathVariable Long fileId,
            @PathVariable Integer versionNumber,
            @RequestParam(defaultValue = "1") Long userId) {
        fileVersionService.restoreVersion(fileId, versionNumber, userId);
        return Result.success();
    }

    @PostMapping("/create/{fileId}")
    public Result<FileVersion> createNewVersion(
            @PathVariable Long fileId,
            @RequestParam String newObjectId,
            @RequestParam String fileMd5,
            @RequestParam Long fileSize,
            @RequestParam(defaultValue = "1") Long userId,
            @RequestParam(required = false) String changeDescription) {
        FileVersion version = fileVersionService.createNewVersion(
                fileId, newObjectId, fileMd5, fileSize, userId, changeDescription);
        return Result.success(version);
    }
}

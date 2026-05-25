package com.filetransfer.controller;

import com.filetransfer.common.Result;
import com.filetransfer.dto.CreateDistributionRequest;
import com.filetransfer.dto.DistributionDetailDTO;
import com.filetransfer.entity.FileDistribution;
import com.filetransfer.repository.DistributionFileRepository;
import com.filetransfer.service.FileDistributionService;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.apache.tomcat.util.http.fileupload.IOUtils;
import org.springframework.web.bind.annotation.*;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

@RestController
@RequestMapping("/distribution")
@RequiredArgsConstructor
public class FileDistributionController {
    private final FileDistributionService distributionService;
    private final DistributionFileRepository distributionFileRepository;

    @PostMapping("/create")
    public Result<FileDistribution> createDistribution(
            @Valid @RequestBody CreateDistributionRequest request) {
        FileDistribution distribution = distributionService.createDistribution(request);
        return Result.success(distribution);
    }

    @GetMapping("/detail/{distributionId}")
    public Result<DistributionDetailDTO> getDistributionDetail(
            @PathVariable String distributionId,
            @RequestParam(required = false) String recipientId) {
        DistributionDetailDTO detail = distributionService.getDistributionDetail(distributionId, recipientId);
        return Result.success(detail);
    }

    @GetMapping("/download/{distributionId}/{fileId}")
    public void downloadFile(
            @PathVariable String distributionId,
            @PathVariable Long fileId,
            @RequestParam(required = false) String recipientId,
            HttpServletResponse response) {
        try {
            var distributionFile = distributionFileRepository
                    .findByDistributionIdOrderByCreatedAtDesc(distributionId)
                    .stream().filter(f -> f.getFileId().equals(fileId)).findFirst()
                    .orElseThrow(() -> new RuntimeException("文件不存在"));

            InputStream inputStream = distributionService.downloadDistributionFile(
                    distributionId, fileId, recipientId);

            response.setContentType(distributionFile.getContentType());
            response.setHeader("Content-Disposition", "attachment; filename*=UTF-8''"
                    + URLEncoder.encode(distributionFile.getFileName(), StandardCharsets.UTF_8));

            try (OutputStream outputStream = response.getOutputStream()) {
                IOUtils.copy(inputStream, outputStream);
                outputStream.flush();
            }
        } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/user/list")
    public Result<List<FileDistribution>> getUserDistributions(
            @RequestParam(defaultValue = "1") Long userId) {
        List<FileDistribution> distributions = distributionService.getUserDistributions(userId);
        return Result.success(distributions);
    }

    @PostMapping("/cancel/{distributionId}")
    public Result<Void> cancelDistribution(
            @PathVariable String distributionId,
            @RequestParam(defaultValue = "1") Long userId) {
        distributionService.cancelDistribution(distributionId, userId);
        return Result.success();
    }
}

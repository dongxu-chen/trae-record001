package com.voting.controller;

import com.voting.service.ExportService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@RestController
@RequestMapping("/api/export")
@CrossOrigin(origins = "*")
public class ExportController {

    @Autowired
    private ExportService exportService;

    @GetMapping("/result/{voteId}")
    public ResponseEntity<byte[]> exportVoteResult(@PathVariable Long voteId) {
        try {
            byte[] data = exportService.exportVoteResultToCSV(voteId);
            String filename = URLEncoder.encode("投票结果_" + voteId + ".csv", StandardCharsets.UTF_8);

            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + filename)
                    .contentType(MediaType.parseMediaType("text/csv; charset=UTF-8"))
                    .body(data);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    @GetMapping("/records/{voteId}")
    public ResponseEntity<byte[]> exportVoteRecords(@PathVariable Long voteId) {
        try {
            byte[] data = exportService.exportVoteRecordsToCSV(voteId);
            String filename = URLEncoder.encode("投票记录_" + voteId + ".csv", StandardCharsets.UTF_8);

            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + filename)
                    .contentType(MediaType.parseMediaType("text/csv; charset=UTF-8"))
                    .body(data);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }
}

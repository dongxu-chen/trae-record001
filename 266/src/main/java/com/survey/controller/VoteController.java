package com.survey.controller;

import com.survey.dto.VoteSubmitRequest;
import com.survey.entity.VoteRecord;
import com.survey.service.VoteService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/votes")
@RequiredArgsConstructor
@Tag(name = "投票管理", description = "投票提交、查询等接口")
public class VoteController {

    private final VoteService voteService;

    @PostMapping
    @Operation(summary = "提交投票")
    public ResponseEntity<VoteRecord> submitVote(@Valid @RequestBody VoteSubmitRequest request,
                                                 HttpServletRequest httpRequest) {
        return ResponseEntity.ok(voteService.submitVote(request, httpRequest));
    }

    @GetMapping("/survey/{surveyId}")
    @Operation(summary = "获取问卷的投票记录")
    public ResponseEntity<List<VoteRecord>> getVoteRecords(@PathVariable String surveyId) {
        return ResponseEntity.ok(voteService.getVoteRecords(surveyId));
    }
}

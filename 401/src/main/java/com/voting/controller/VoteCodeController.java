package com.voting.controller;

import com.voting.common.Result;
import com.voting.service.VoteCodeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/vote-codes")
@CrossOrigin(origins = "*")
public class VoteCodeController {

    @Autowired
    private VoteCodeService voteCodeService;

    @PostMapping("/generate/{voteId}")
    public Result<List<String>> generateVoteCodes(@PathVariable Long voteId,
                                                   @RequestParam(defaultValue = "10") int count,
                                                   @RequestParam(required = false) Integer expireDays) {
        if (count <= 0 || count > 1000) {
            return Result.error("生成数量必须在1-1000之间");
        }
        if (expireDays != null && (expireDays < 1 || expireDays > 365)) {
            return Result.error("有效期必须在1-365天之间");
        }
        List<String> codes;
        if (expireDays != null) {
            codes = voteCodeService.generateVoteCodes(voteId, count, expireDays);
        } else {
            codes = voteCodeService.generateVoteCodes(voteId, count);
        }
        return Result.success(codes);
    }

    @GetMapping("/validate/{voteId}")
    public Result<Boolean> validateVoteCode(@PathVariable Long voteId,
                                            @RequestParam String code) {
        boolean valid = voteCodeService.validateVoteCode(voteId, code);
        return Result.success(valid);
    }

    @GetMapping("/count/{voteId}")
    public Result<Long> getUsedCodeCount(@PathVariable Long voteId) {
        long count = voteCodeService.getUsedCodeCount(voteId);
        return Result.success(count);
    }
}

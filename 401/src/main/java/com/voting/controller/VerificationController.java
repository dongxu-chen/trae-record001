package com.voting.controller;

import com.voting.common.Result;
import com.voting.dto.VoteResultDTO;
import com.voting.service.VerificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/verification")
@CrossOrigin(origins = "*")
public class VerificationController {

    @Autowired
    private VerificationService verificationService;

    @GetMapping("/data/{voteId}")
    public Result<Map<String, Object>> getVerificationData(@PathVariable Long voteId) {
        try {
            Map<String, Object> data = verificationService.generateVerificationData(voteId);
            return Result.success(data);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/verify-result")
    public Result<Map<String, Object>> verifyVoteResult(@RequestBody VoteResultDTO expectedResult) {
        try {
            Map<String, Object> result = verificationService.verifyVoteResult(expectedResult);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/verify-receipt/{recordHash}")
    public Result<Boolean> verifyReceiptInclusion(@PathVariable String recordHash) {
        boolean valid = verificationService.verifyReceiptInclusion(recordHash);
        return Result.success(valid);
    }

    @GetMapping("/blockchain-info")
    public Result<Map<String, Object>> getBlockchainInfo() {
        Map<String, Object> info = verificationService.getBlockchainInfo();
        return Result.success(info);
    }
}

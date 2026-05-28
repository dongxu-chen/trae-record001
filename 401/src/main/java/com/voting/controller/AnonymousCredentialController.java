package com.voting.controller;

import com.voting.common.Result;
import com.voting.service.AnonymousCredentialService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/credentials")
@CrossOrigin(origins = "*")
public class AnonymousCredentialController {

    @Autowired
    private AnonymousCredentialService credentialService;

    @PostMapping("/generate/{voteId}")
    public Result<List<String>> generateCredentials(@PathVariable Long voteId,
                                                     @RequestParam(defaultValue = "10") int count,
                                                     @RequestParam(required = false) Integer expireDays) {
        if (count <= 0 || count > 1000) {
            return Result.error("生成数量必须在1-1000之间");
        }
        if (expireDays != null && (expireDays < 1 || expireDays > 365)) {
            return Result.error("有效期必须在1-365天之间");
        }

        List<String> secrets;
        if (expireDays != null) {
            secrets = credentialService.generateCredentials(voteId, count, expireDays);
        } else {
            secrets = credentialService.generateCredentials(voteId, count);
        }
        return Result.success(secrets);
    }

    @PostMapping("/generate-proof")
    public Result<String> generateProof(@RequestParam String secret,
                                         @RequestParam Long voteId) {
        String proof = credentialService.generateZkProof(secret, voteId);
        return Result.success(proof);
    }

    @GetMapping("/verify")
    public Result<Boolean> verifyCredential(@RequestParam String proof,
                                             @RequestParam Long voteId) {
        boolean valid = credentialService.verifyCredential(proof, voteId);
        return Result.success(valid);
    }

    @GetMapping("/nullifier-used/{nullifier}")
    public Result<Boolean> isNullifierUsed(@PathVariable String nullifier) {
        boolean used = credentialService.isNullifierUsed(nullifier);
        return Result.success(used);
    }
}

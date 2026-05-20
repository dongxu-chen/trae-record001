package com.econtract.controller;

import com.econtract.common.Result;
import com.econtract.entity.WitnessAuth;
import com.econtract.service.WitnessAuthService;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.io.IOException;
import java.util.Map;

@RestController
@RequestMapping("/witness")
public class WitnessAuthController {

    @Resource
    private WitnessAuthService witnessAuthService;

    @PostMapping("/start/{contractId}")
    public Result<Map<String, Object>> startWitnessAuth(@PathVariable Long contractId) {
        return Result.success(witnessAuthService.startWitnessAuth(contractId));
    }

    @PostMapping("/submit")
    public Result<Map<String, Object>> submitWitnessVideo(
            @RequestParam Long authId,
            @RequestParam("videoFile") MultipartFile videoFile,
            @RequestParam(required = false) Integer duration,
            @RequestParam(required = false) String speechText) throws IOException {
        return Result.success(witnessAuthService.submitWitnessVideo(
                authId, videoFile, duration, speechText));
    }

    @GetMapping("/{authId}")
    public Result<Map<String, Object>> getWitnessAuth(@PathVariable Long authId) {
        return Result.success(witnessAuthService.verifyWitnessAuth(authId));
    }

    @GetMapping("/contract/{contractId}/signer/{signerId}")
    public Result<WitnessAuth> getWitnessAuthByContractAndSigner(
            @PathVariable Long contractId,
            @PathVariable Long signerId) {
        return Result.success(witnessAuthService.getWitnessAuthByContractAndSigner(
                contractId, signerId));
    }
}

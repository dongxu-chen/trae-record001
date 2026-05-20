package com.econtract.controller;

import com.econtract.common.Result;
import com.econtract.entity.ContractVerifyLog;
import com.econtract.service.ContractVerifyService;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/verify")
public class ContractVerifyController {

    @Resource
    private ContractVerifyService verifyService;

    @GetMapping("/public")
    public Result<Map<String, Object>> verifyContractPublic(
            @RequestParam String contractNo) {
        return Result.success(verifyService.verifyContract(contractNo, "PUBLIC"));
    }

    @GetMapping("/internal")
    public Result<Map<String, Object>> verifyContractInternal(
            @RequestParam String contractNo) {
        return Result.success(verifyService.verifyContract(contractNo, "INTERNAL"));
    }

    @GetMapping("/logs/{contractNo}")
    public Result<List<ContractVerifyLog>> getVerifyLogs(@PathVariable String contractNo) {
        return Result.success(verifyService.getVerifyLogs(contractNo));
    }
}

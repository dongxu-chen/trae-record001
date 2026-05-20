package com.econtract.controller;

import com.econtract.common.Result;
import com.econtract.entity.ContractReview;
import com.econtract.service.ContractReviewService;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.Map;

@RestController
@RequestMapping("/review")
public class ContractReviewController {

    @Resource
    private ContractReviewService reviewService;

    @PostMapping("/contract/{contractId}")
    public Result<Map<String, Object>> reviewContract(@PathVariable Long contractId) {
        return Result.success(reviewService.reviewContract(contractId));
    }

    @GetMapping("/contract/{contractId}")
    public Result<ContractReview> getReview(@PathVariable Long contractId) {
        return Result.success(reviewService.getReviewByContractId(contractId));
    }
}

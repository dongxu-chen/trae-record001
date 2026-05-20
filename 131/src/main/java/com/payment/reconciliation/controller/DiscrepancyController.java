package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.dto.DiscrepancyHandleDTO;
import com.payment.reconciliation.entity.Discrepancy;
import com.payment.reconciliation.service.DiscrepancyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/discrepancy")
public class DiscrepancyController {

    @Autowired
    private DiscrepancyService discrepancyService;

    @GetMapping("/list")
    public Result<List<Discrepancy>> listDiscrepancies(
            @RequestParam(required = false) String channelCode,
            @RequestParam(required = false) Integer type,
            @RequestParam(required = false) Integer status) {
        List<Discrepancy> list = discrepancyService.listDiscrepancies(channelCode, type, status);
        return Result.success(list);
    }

    @GetMapping("/{id}")
    public Result<Discrepancy> getDiscrepancyById(@PathVariable Long id) {
        Discrepancy discrepancy = discrepancyService.getDiscrepancyById(id);
        return Result.success(discrepancy);
    }

    @PostMapping("/handle")
    public Result<Void> handleDiscrepancy(
            @Validated @RequestBody DiscrepancyHandleDTO dto) {
        discrepancyService.handleDiscrepancy(dto);
        return Result.success();
    }
}

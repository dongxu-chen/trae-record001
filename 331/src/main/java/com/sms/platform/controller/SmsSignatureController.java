package com.sms.platform.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.sms.platform.common.Result;
import com.sms.platform.entity.SmsSignature;
import com.sms.platform.service.SmsSignatureService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/v1/signature")
public class SmsSignatureController {

    @Resource
    private SmsSignatureService signatureService;

    @PostMapping
    public Result<Void> addSignature(@RequestBody SmsSignature signature) {
        log.info("添加签名: {}", signature.getSignatureName());
        signatureService.addSignature(signature);
        return Result.success();
    }

    @PutMapping
    public Result<Void> updateSignature(@RequestBody SmsSignature signature) {
        log.info("更新签名: id={}", signature.getId());
        signatureService.updateSignature(signature);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteSignature(@PathVariable Long id) {
        log.info("删除签名: id={}", id);
        signatureService.deleteSignature(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<SmsSignature> getSignature(@PathVariable Long id) {
        return Result.success(signatureService.getSignature(id));
    }

    @GetMapping("/page")
    public Result<Page<SmsSignature>> listSignatures(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) Integer smsType,
            @RequestParam(required = false) Integer channelCode,
            @RequestParam(required = false) Integer status) {
        return Result.success(signatureService.listSignatures(pageNum, pageSize, smsType, channelCode, status));
    }

    @GetMapping("/list")
    public Result<List<SmsSignature>> listAllSignatures() {
        return Result.success(signatureService.listAllSignatures());
    }
}

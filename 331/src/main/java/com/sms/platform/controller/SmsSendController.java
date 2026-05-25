package com.sms.platform.controller;

import com.sms.platform.common.Result;
import com.sms.platform.dto.SendSmsDTO;
import com.sms.platform.dto.SmsSendResult;
import com.sms.platform.service.SmsSendService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import javax.validation.Valid;
import javax.validation.constraints.NotBlank;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Validated
@RestController
@RequestMapping("/api/v1/sms")
public class SmsSendController {

    @Resource
    private SmsSendService smsSendService;

    @PostMapping("/send")
    public Result<SmsSendResult> sendSms(@Valid @RequestBody SendSmsDTO dto) {
        log.info("收到短信发送请求, mobile={}, smsType={}, templateCode={}", dto.getMobile(), dto.getSmsType(), dto.getTemplateCode());
        SmsSendResult result = smsSendService.sendSms(dto);
        return Result.success(result);
    }

    @PostMapping("/send/verification")
    public Result<SmsSendResult> sendVerificationCode(@RequestParam @NotBlank(message = "手机号不能为空") String mobile) {
        log.info("收到验证码发送请求, mobile={}", mobile);
        SendSmsDTO dto = new SendSmsDTO();
        dto.setMobile(mobile);
        dto.setSmsType(1);
        dto.setTemplateCode("VERIFY_CODE");
        SmsSendResult result = smsSendService.sendSms(dto);
        return Result.success(result);
    }

    @PostMapping("/verify")
    public Result<Map<String, Boolean>> verifyCode(
            @RequestParam @NotBlank(message = "手机号不能为空") String mobile,
            @RequestParam @NotBlank(message = "验证码不能为空") String code) {
        log.info("收到验证码验证请求, mobile={}", mobile);
        boolean valid = smsSendService.verifyCode(mobile, code);
        Map<String, Boolean> data = new HashMap<>();
        data.put("valid", valid);
        return Result.success(data);
    }
}

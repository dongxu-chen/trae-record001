package com.econtract.controller;

import com.econtract.common.Result;
import com.econtract.dto.SmsSendDTO;
import com.econtract.service.SmsService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;

@RestController
@RequestMapping("/sms")
public class SmsController {

    @Resource
    private SmsService smsService;

    @PostMapping("/send")
    public Result<Void> sendSms(@Validated @RequestBody SmsSendDTO smsSendDTO) {
        smsService.sendSms(smsSendDTO.getPhone(), smsSendDTO.getBizType());
        return Result.success("验证码已发送，请注意查收", null);
    }
}

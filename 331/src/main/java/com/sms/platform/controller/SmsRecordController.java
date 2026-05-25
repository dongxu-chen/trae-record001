package com.sms.platform.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.sms.platform.common.Result;
import com.sms.platform.entity.SmsSendRecord;
import com.sms.platform.service.SmsSendRecordService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/record")
public class SmsRecordController {

    @Resource
    private SmsSendRecordService sendRecordService;

    @GetMapping("/page")
    public Result<Page<SmsSendRecord>> listRecords(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) String mobile,
            @RequestParam(required = false) Integer smsType,
            @RequestParam(required = false) Integer channelCode,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime) {
        return Result.success(sendRecordService.listRecords(pageNum, pageSize, mobile, smsType, channelCode, status, startTime, endTime));
    }

    @GetMapping("/{id}")
    public Result<SmsSendRecord> getRecord(@PathVariable Long id) {
        return Result.success(sendRecordService.getRecord(id));
    }

    @GetMapping("/serial/{serialNo}")
    public Result<SmsSendRecord> getRecordBySerialNo(@PathVariable String serialNo) {
        return Result.success(sendRecordService.getRecordBySerialNo(serialNo));
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> getStatistics(
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        return Result.success(sendRecordService.getStatistics(startDate, endDate));
    }

    @GetMapping("/trend")
    public Result<List<Map<String, Object>>> getTrendStatistics(@RequestParam(defaultValue = "7") int days) {
        return Result.success(sendRecordService.getTrendStatistics(days));
    }
}

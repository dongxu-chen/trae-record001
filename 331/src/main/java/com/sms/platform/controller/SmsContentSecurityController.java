package com.sms.platform.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sms.platform.common.Result;
import com.sms.platform.entity.SmsSensitiveKeyword;
import com.sms.platform.mapper.SmsSensitiveKeywordMapper;
import com.sms.platform.service.ContentSecurityService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/sms/security")
public class SmsContentSecurityController {

    @Resource
    private ContentSecurityService contentSecurityService;

    @Resource
    private SmsSensitiveKeywordMapper sensitiveKeywordMapper;

    @PostMapping("/check")
    public Result<ContentSecurityService.SecurityCheckResult> checkContent(@RequestBody Map<String, String> params) {
        String content = params.get("content");
        if (content == null || content.isEmpty()) {
            return Result.error("检测内容不能为空");
        }
        ContentSecurityService.SecurityCheckResult result = contentSecurityService.checkContent(content);
        return Result.success(result);
    }

    @PostMapping("/keyword")
    public Result<String> addKeyword(@RequestBody SmsSensitiveKeyword keyword) {
        contentSecurityService.addKeyword(keyword);
        return Result.success("添加成功");
    }

    @PostMapping("/keyword/batch")
    public Result<String> addKeywordsBatch(@RequestBody List<SmsSensitiveKeyword> keywords) {
        contentSecurityService.addKeywordsBatch(keywords);
        return Result.success("批量添加成功，共 " + keywords.size() + " 条");
    }

    @DeleteMapping("/keyword/{id}")
    public Result<String> removeKeyword(@PathVariable Long id) {
        contentSecurityService.removeKeyword(id);
        return Result.success("删除成功");
    }

    @PutMapping("/keyword")
    public Result<String> updateKeyword(@RequestBody SmsSensitiveKeyword keyword) {
        contentSecurityService.updateKeyword(keyword);
        return Result.success("更新成功");
    }

    @GetMapping("/keyword/{id}")
    public Result<SmsSensitiveKeyword> getKeyword(@PathVariable Long id) {
        SmsSensitiveKeyword keyword = sensitiveKeywordMapper.selectById(id);
        if (keyword == null || keyword.getDeleted() == 1) {
            return Result.error("关键词不存在");
        }
        return Result.success(keyword);
    }

    @GetMapping("/keyword/list")
    public Result<List<SmsSensitiveKeyword>> listKeywords(
            @RequestParam(required = false) Integer category,
            @RequestParam(required = false) Integer riskLevel,
            @RequestParam(required = false) String keyword) {
        LambdaQueryWrapper<SmsSensitiveKeyword> wrapper = new LambdaQueryWrapper<SmsSensitiveKeyword>()
                .eq(SmsSensitiveKeyword::getDeleted, 0)
                .orderByDesc(SmsSensitiveKeyword::getCreateTime);

        if (category != null) {
            wrapper.eq(SmsSensitiveKeyword::getCategory, category);
        }
        if (riskLevel != null) {
            wrapper.eq(SmsSensitiveKeyword::getRiskLevel, riskLevel);
        }
        if (keyword != null && !keyword.isEmpty()) {
            wrapper.like(SmsSensitiveKeyword::getKeyword, keyword);
        }

        return Result.success(sensitiveKeywordMapper.selectList(wrapper));
    }

    @GetMapping("/stats")
    public Result<Map<String, Object>> getKeywordStats() {
        return Result.success(contentSecurityService.getKeywordStats());
    }

    @PostMapping("/refresh")
    public Result<String> refreshCache() {
        contentSecurityService.refreshKeywordCache();
        return Result.success("缓存刷新成功");
    }

    @GetMapping("/status")
    public Result<Map<String, Object>> getStatus() {
        return Result.success(contentSecurityService.getServiceStatus());
    }
}

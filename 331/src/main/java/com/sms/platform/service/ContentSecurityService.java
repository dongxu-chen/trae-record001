package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sms.platform.common.enums.ContentSecurityStatusEnum;
import com.sms.platform.common.enums.RiskLevelEnum;
import com.sms.platform.common.enums.SensitiveCategoryEnum;
import com.sms.platform.entity.SmsSensitiveKeyword;
import com.sms.platform.mapper.SmsSensitiveKeywordMapper;
import com.sms.platform.util.RedisUtil;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ContentSecurityService {

    @Resource
    private SmsSensitiveKeywordMapper sensitiveKeywordMapper;

    @Resource
    private RedisUtil redisUtil;

    private static final String SENSITIVE_KEYWORDS_KEY = "sms:security:keywords";
    private static final String CACHE_VERSION_KEY = "sms:security:version";

    private final Map<Integer, List<SmsSensitiveKeyword>> keywordByCategoryCache = new ConcurrentHashMap<>();
    private final Map<String, SmsSensitiveKeyword> keywordMapCache = new ConcurrentHashMap<>();
    private volatile long cacheVersion = 0;

    @PostConstruct
    public void init() {
        refreshKeywordCache();
        log.info("内容安全服务初始化完成，共加载 {} 个敏感词", keywordMapCache.size());
    }

    public SecurityCheckResult checkContent(String content) {
        SecurityCheckResult result = new SecurityCheckResult();
        result.setContent(content);

        if (content == null || content.isEmpty()) {
            result.setPassed(true);
            result.setStatus(ContentSecurityStatusEnum.PASSED.getCode());
            result.setRiskLevel(RiskLevelEnum.NONE.getCode());
            return result;
        }

        ensureCacheFresh();

        List<String> hitKeywords = new ArrayList<>();
        int maxRiskLevel = RiskLevelEnum.NONE.getCode();
        Set<Integer> hitCategories = new HashSet<>();

        String lowerContent = content.toLowerCase();

        for (Map.Entry<String, SmsSensitiveKeyword> entry : keywordMapCache.entrySet()) {
            String keyword = entry.getKey();
            SmsSensitiveKeyword keywordObj = entry.getValue();

            if (keywordObj.getStatus() != 1) {
                continue;
            }

            if (lowerContent.contains(keyword.toLowerCase())) {
                hitKeywords.add(keyword);
                hitCategories.add(keywordObj.getCategory());

                if (keywordObj.getRiskLevel() > maxRiskLevel) {
                    maxRiskLevel = keywordObj.getRiskLevel();
                }
            }
        }

        if (!hitKeywords.isEmpty()) {
            result.setPassed(false);
            result.setStatus(ContentSecurityStatusEnum.REJECTED.getCode());
            result.setRiskLevel(maxRiskLevel);
            result.setHitKeywords(hitKeywords);
            result.setHitCategories(new ArrayList<>(hitCategories));

            String keywordStr = String.join(",", hitKeywords);
            result.setHitKeywordsStr(keywordStr);

            log.warn("内容安全检测不通过, 命中关键词: {}, 风险等级: {}, 内容: {}", keywordStr, maxRiskLevel, content);
        } else {
            result.setPassed(true);
            result.setStatus(ContentSecurityStatusEnum.PASSED.getCode());
            result.setRiskLevel(RiskLevelEnum.NONE.getCode());
        }

        return result;
    }

    public SecurityCheckResult checkContentByCategory(String content, Integer category) {
        SecurityCheckResult result = checkContent(content);
        if (!result.isPassed()) {
            if (category != null && result.getHitCategories() != null) {
                boolean categoryHit = result.getHitCategories().contains(category);
                if (!categoryHit) {
                    result.setPassed(true);
                    result.setStatus(ContentSecurityStatusEnum.PASSED.getCode());
                    result.setRiskLevel(RiskLevelEnum.NONE.getCode());
                }
            }
        }
        return result;
    }

    public void addKeyword(SmsSensitiveKeyword keyword) {
        LambdaQueryWrapper<SmsSensitiveKeyword> existsWrapper = new LambdaQueryWrapper<SmsSensitiveKeyword>()
                .eq(SmsSensitiveKeyword::getKeyword, keyword.getKeyword())
                .eq(SmsSensitiveKeyword::getDeleted, 0);
        if (sensitiveKeywordMapper.selectOne(existsWrapper) != null) {
            throw new com.sms.platform.common.exception.BusinessException("敏感词已存在");
        }

        sensitiveKeywordMapper.insert(keyword);
        refreshKeywordCache();
        log.info("添加敏感词成功: {}, 分类: {}, 风险等级: {}", keyword.getKeyword(), keyword.getCategory(), keyword.getRiskLevel());
    }

    public void addKeywordBatch(List<SmsSensitiveKeyword> keywords) {
        for (SmsSensitiveKeyword keyword : keywords) {
            try {
                addKeyword(keyword);
            } catch (Exception e) {
                log.warn("批量添加敏感词跳过已存在的词: {}", keyword.getKeyword());
            }
        }
    }

    public void removeKeyword(Long id) {
        SmsSensitiveKeyword keyword = sensitiveKeywordMapper.selectById(id);
        if (keyword != null && keyword.getDeleted() == 0) {
            keyword.setDeleted(1);
            sensitiveKeywordMapper.updateById(keyword);
            refreshKeywordCache();
            log.info("删除敏感词成功: {}", keyword.getKeyword());
        }
    }

    public void removeKeywordByKeyword(String keyword) {
        LambdaQueryWrapper<SmsSensitiveKeyword> wrapper = new LambdaQueryWrapper<SmsSensitiveKeyword>()
                .eq(SmsSensitiveKeyword::getKeyword, keyword)
                .eq(SmsSensitiveKeyword::getDeleted, 0);
        SmsSensitiveKeyword keywordObj = sensitiveKeywordMapper.selectOne(wrapper);
        if (keywordObj != null) {
            removeKeyword(keywordObj.getId());
        }
    }

    public List<SmsSensitiveKeyword> listKeywords(Integer category, Integer riskLevel, Integer status) {
        LambdaQueryWrapper<SmsSensitiveKeyword> wrapper = new LambdaQueryWrapper<SmsSensitiveKeyword>()
                .eq(SmsSensitiveKeyword::getDeleted, 0)
                .orderByDesc(SmsSensitiveKeyword::getRiskLevel, SmsSensitiveKeyword::getCreateTime);

        if (category != null) {
            wrapper.eq(SmsSensitiveKeyword::getCategory, category);
        }
        if (riskLevel != null) {
            wrapper.eq(SmsSensitiveKeyword::getRiskLevel, riskLevel);
        }
        if (status != null) {
            wrapper.eq(SmsSensitiveKeyword::getStatus, status);
        }

        return sensitiveKeywordMapper.selectList(wrapper);
    }

    public Map<String, Object> getKeywordStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalCount", keywordMapCache.size());

        Map<Integer, Long> categoryCount = new HashMap<>();
        Map<Integer, Long> riskCount = new HashMap<>();

        for (SensitiveCategoryEnum category : SensitiveCategoryEnum.values()) {
            List<SmsSensitiveKeyword> keywords = keywordByCategoryCache.get(category.getCode());
            if (keywords != null) {
                categoryCount.put(category.getCode(), (long) keywords.size());
            } else {
                categoryCount.put(category.getCode(), 0L);
            }
        }

        for (RiskLevelEnum level : RiskLevelEnum.values()) {
            if (level == RiskLevelEnum.NONE) continue;
            long count = keywordMapCache.values().stream()
                    .filter(k -> k.getRiskLevel() != null && k.getRiskLevel().equals(level.getCode()))
                    .count();
            riskCount.put(level.getCode(), count);
        }

        stats.put("categoryCount", categoryCount);
        stats.put("riskCount", riskCount);
        stats.put("cacheVersion", cacheVersion);

        return stats;
    }

    public void refreshKeywordCache() {
        List<SmsSensitiveKeyword> allKeywords = sensitiveKeywordMapper.selectList(
                new LambdaQueryWrapper<SmsSensitiveKeyword>()
                        .eq(SmsSensitiveKeyword::getStatus, 1)
                        .eq(SmsSensitiveKeyword::getDeleted, 0)
        );

        keywordByCategoryCache.clear();
        keywordMapCache.clear();

        for (SmsSensitiveKeyword keyword : allKeywords) {
            keywordMapCache.put(keyword.getKeyword(), keyword);
            keywordByCategoryCache
                    .computeIfAbsent(keyword.getCategory(), k -> new ArrayList<>())
                    .add(keyword);
        }

        cacheVersion++;
        redisUtil.set(CACHE_VERSION_KEY, cacheVersion);

        try {
            Map<String, Object> keywordMap = new HashMap<>();
            for (SmsSensitiveKeyword keyword : allKeywords) {
                Map<String, Object> keywordData = new HashMap<>();
                keywordData.put("category", keyword.getCategory());
                keywordData.put("riskLevel", keyword.getRiskLevel());
                keywordMap.put(keyword.getKeyword(), keywordData);
            }
            redisUtil.hSetAll(SENSITIVE_KEYWORDS_KEY, keywordMap);
        } catch (Exception e) {
            log.error("同步敏感词到Redis失败", e);
        }

        log.info("敏感词缓存已刷新, 共 {} 个, 版本: {}", keywordMapCache.size(), cacheVersion);
    }

    private void ensureCacheFresh() {
        try {
            Object redisVersion = redisUtil.get(CACHE_VERSION_KEY);
            if (redisVersion != null) {
                long rv = ((Number) redisVersion).longValue();
                if (rv > cacheVersion) {
                    log.info("检测到Redis缓存版本更新，刷新本地缓存");
                    refreshKeywordCache();
                }
            }
        } catch (Exception e) {
            log.debug("检查缓存版本失败，使用本地缓存");
        }
    }

    @Data
    public static class SecurityCheckResult {
        private boolean passed;
        private Integer status;
        private Integer riskLevel;
        private String content;
        private List<String> hitKeywords;
        private List<Integer> hitCategories;
        private String hitKeywordsStr;
    }
}

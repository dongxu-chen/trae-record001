package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sms.platform.common.exception.BusinessException;
import com.sms.platform.entity.SmsBlacklist;
import com.sms.platform.mapper.SmsBlacklistMapper;
import com.sms.platform.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

@Slf4j
@Service
public class BlacklistService {

    @Resource
    private SmsBlacklistMapper blacklistMapper;

    @Resource
    private RedisUtil redisUtil;

    private static final String BLACKLIST_KEY_PREFIX = "sms:blacklist:";
    private static final String BLACKLIST_PREFIX_KEY = "sms:blacklist:prefix:";
    private static final String EXACT_MATCH_SUFFIX = ":exact:";
    private static final String PREFIX_MATCH_SUFFIX = ":prefix:";

    private final ConcurrentHashMap<String, SmsBlacklist> exactBlacklistCache = new ConcurrentHashMap<>();
    private final TreeMap<String, SmsBlacklist> prefixBlacklistCache = new TreeMap<>(Comparator.reverseOrder());

    private static final Pattern MOBILE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");
    private static final Pattern PREFIX_PATTERN = Pattern.compile("^1[3-9]\\d{0,9}$");

    @PostConstruct
    public void init() {
        loadBlacklistToCache();
        log.info("黑名单服务初始化完成，精确匹配: {} 条, 前缀匹配: {} 条",
                exactBlacklistCache.size(), prefixBlacklistCache.size());
    }

    private void loadBlacklistToCache() {
        List<SmsBlacklist> blacklists = blacklistMapper.selectList(
                new LambdaQueryWrapper<SmsBlacklist>()
                        .eq(SmsBlacklist::getDeleted, 0)
        );

        for (SmsBlacklist item : blacklists) {
            if (isExpired(item)) {
                continue;
            }

            if (item.getIsPrefixMatch() != null && item.getIsPrefixMatch() == 1) {
                String cacheKey = buildPrefixCacheKey(item.getMobile(), item.getSmsType());
                prefixBlacklistCache.put(cacheKey, item);
            } else {
                String cacheKey = buildExactCacheKey(item.getMobile(), item.getSmsType());
                exactBlacklistCache.put(cacheKey, item);
            }
        }
    }

    public boolean isBlacklisted(String mobile, Integer smsType) {
        if (checkExactMatch(mobile, smsType)) {
            return true;
        }

        if (checkPrefixMatch(mobile, smsType)) {
            return true;
        }

        if (checkRedisExactBlacklist(mobile, smsType)) {
            return true;
        }

        if (checkRedisPrefixBlacklist(mobile, smsType)) {
            return true;
        }

        return checkDbBlacklist(mobile, smsType);
    }

    private boolean checkExactMatch(String mobile, Integer smsType) {
        String allTypeKey = buildExactCacheKey(mobile, null);
        SmsBlacklist allTypeItem = exactBlacklistCache.get(allTypeKey);
        if (allTypeItem != null && !isExpired(allTypeItem)) {
            log.info("手机号 {} 在精确匹配全局黑名单中，拦截发送", mobile);
            return true;
        }

        String typeKey = buildExactCacheKey(mobile, smsType);
        SmsBlacklist typeItem = exactBlacklistCache.get(typeKey);
        if (typeItem != null && !isExpired(typeItem)) {
            log.info("手机号 {} 在精确匹配短信类型 {} 的黑名单中，拦截发送", mobile, smsType);
            return true;
        }

        return false;
    }

    private boolean checkPrefixMatch(String mobile, Integer smsType) {
        for (Map.Entry<String, SmsBlacklist> entry : prefixBlacklistCache.entrySet()) {
            String cacheKey = entry.getKey();
            SmsBlacklist item = entry.getValue();

            if (isExpired(item)) {
                continue;
            }

            String prefix = item.getMobile();
            Integer type = item.getSmsType();

            if (mobile.startsWith(prefix)) {
                if (type == null || type.equals(smsType)) {
                    String exactKey = buildExactCacheKey(mobile, type);
                    exactBlacklistCache.put(exactKey, item);
                    addToRedis(item);
                    log.info("手机号 {} 匹配前缀黑名单规则: {} (类型: {}), 拦截发送", mobile, prefix, type);
                    return true;
                }
            }
        }

        return false;
    }

    private boolean checkRedisExactBlacklist(String mobile, Integer smsType) {
        String allTypeRedisKey = BLACKLIST_KEY_PREFIX + EXACT_MATCH_SUFFIX + mobile + ":all";
        if (Boolean.TRUE.equals(redisUtil.hasKey(allTypeRedisKey))) {
            String cacheKey = buildExactCacheKey(mobile, null);
            SmsBlacklist item = new SmsBlacklist();
            item.setMobile(mobile);
            item.setSmsType(null);
            item.setIsPrefixMatch(0);
            exactBlacklistCache.put(cacheKey, item);
            log.info("手机号 {} 在Redis精确匹配全局黑名单中，拦截发送", mobile);
            return true;
        }

        String typeRedisKey = BLACKLIST_KEY_PREFIX + EXACT_MATCH_SUFFIX + mobile + ":" + smsType;
        if (Boolean.TRUE.equals(redisUtil.hasKey(typeRedisKey))) {
            String cacheKey = buildExactCacheKey(mobile, smsType);
            SmsBlacklist item = new SmsBlacklist();
            item.setMobile(mobile);
            item.setSmsType(smsType);
            item.setIsPrefixMatch(0);
            exactBlacklistCache.put(cacheKey, item);
            log.info("手机号 {} 在Redis精确匹配短信类型 {} 的黑名单中，拦截发送", mobile, smsType);
            return true;
        }

        return false;
    }

    private boolean checkRedisPrefixBlacklist(String mobile, Integer smsType) {
        for (int i = mobile.length(); i >= 1; i--) {
            String prefix = mobile.substring(0, i);

            String allTypeRedisKey = BLACKLIST_PREFIX_KEY + prefix + ":all";
            if (Boolean.TRUE.equals(redisUtil.hasKey(allTypeRedisKey))) {
                SmsBlacklist item = new SmsBlacklist();
                item.setMobile(prefix);
                item.setSmsType(null);
                item.setIsPrefixMatch(1);
                String prefixCacheKey = buildPrefixCacheKey(prefix, null);
                prefixBlacklistCache.put(prefixCacheKey, item);
                log.info("手机号 {} 匹配Redis前缀黑名单规则: {} (类型: all), 拦截发送", mobile, prefix);
                return true;
            }

            String typeRedisKey = BLACKLIST_PREFIX_KEY + prefix + ":" + smsType;
            if (Boolean.TRUE.equals(redisUtil.hasKey(typeRedisKey))) {
                SmsBlacklist item = new SmsBlacklist();
                item.setMobile(prefix);
                item.setSmsType(smsType);
                item.setIsPrefixMatch(1);
                String prefixCacheKey = buildPrefixCacheKey(prefix, smsType);
                prefixBlacklistCache.put(prefixCacheKey, item);
                log.info("手机号 {} 匹配Redis前缀黑名单规则: {} (类型: {}), 拦截发送", mobile, prefix, smsType);
                return true;
            }
        }

        return false;
    }

    private boolean checkDbBlacklist(String mobile, Integer smsType) {
        List<SmsBlacklist> exactBlacklists = blacklistMapper.selectList(
                new LambdaQueryWrapper<SmsBlacklist>()
                        .eq(SmsBlacklist::getMobile, mobile)
                        .eq(SmsBlacklist::getIsPrefixMatch, 0)
                        .eq(SmsBlacklist::getDeleted, 0)
        );

        for (SmsBlacklist item : exactBlacklists) {
            if (isExpired(item)) {
                continue;
            }
            if (item.getSmsType() == null || item.getSmsType().equals(smsType)) {
                String cacheKey = buildExactCacheKey(mobile, item.getSmsType());
                exactBlacklistCache.put(cacheKey, item);
                addToRedis(item);
                log.info("手机号 {} 在DB精确匹配黑名单中，拦截发送，类型: {}", mobile, item.getSmsType());
                return true;
            }
        }

        List<SmsBlacklist> prefixBlacklists = blacklistMapper.selectList(
                new LambdaQueryWrapper<SmsBlacklist>()
                        .eq(SmsBlacklist::getIsPrefixMatch, 1)
                        .eq(SmsBlacklist::getDeleted, 0)
                        .orderByDesc(SmsBlacklist::getMobile)
        );

        for (SmsBlacklist item : prefixBlacklists) {
            if (isExpired(item)) {
                continue;
            }
            if (mobile.startsWith(item.getMobile())) {
                if (item.getSmsType() == null || item.getSmsType().equals(smsType)) {
                    String cacheKey = buildPrefixCacheKey(item.getMobile(), item.getSmsType());
                    prefixBlacklistCache.put(cacheKey, item);
                    addToRedis(item);
                    log.info("手机号 {} 匹配DB前缀黑名单规则: {} (类型: {}), 拦截发送",
                            mobile, item.getMobile(), item.getSmsType());
                    return true;
                }
            }
        }

        return false;
    }

    public void addBlacklist(SmsBlacklist blacklist) {
        validateBlacklist(blacklist);

        LambdaQueryWrapper<SmsBlacklist> existsWrapper = new LambdaQueryWrapper<SmsBlacklist>()
                .eq(SmsBlacklist::getMobile, blacklist.getMobile())
                .eq(SmsBlacklist::getIsPrefixMatch, blacklist.getIsPrefixMatch() != null ? blacklist.getIsPrefixMatch() : 0)
                .eq(SmsBlacklist::getDeleted, 0);
        if (blacklist.getSmsType() != null) {
            existsWrapper.eq(SmsBlacklist::getSmsType, blacklist.getSmsType());
        } else {
            existsWrapper.isNull(SmsBlacklist::getSmsType);
        }

        SmsBlacklist exists = blacklistMapper.selectOne(existsWrapper);
        if (exists != null) {
            throw new BusinessException("该黑名单规则已存在");
        }

        if (blacklist.getIsPrefixMatch() == null) {
            blacklist.setIsPrefixMatch(0);
        }

        blacklistMapper.insert(blacklist);

        String cacheKey;
        if (blacklist.getIsPrefixMatch() == 1) {
            cacheKey = buildPrefixCacheKey(blacklist.getMobile(), blacklist.getSmsType());
            prefixBlacklistCache.put(cacheKey, blacklist);
        } else {
            cacheKey = buildExactCacheKey(blacklist.getMobile(), blacklist.getSmsType());
            exactBlacklistCache.put(cacheKey, blacklist);
        }

        addToRedis(blacklist);

        log.info("添加黑名单成功: mobile={}, smsType={}, isPrefixMatch={}",
                blacklist.getMobile(), blacklist.getSmsType(), blacklist.getIsPrefixMatch());
    }

    public void addPrefixBlacklistBatch(String prefix, Integer smsType, String reason) {
        validatePrefix(prefix);

        SmsBlacklist blacklist = new SmsBlacklist();
        blacklist.setMobile(prefix);
        blacklist.setSmsType(smsType);
        blacklist.setIsPrefixMatch(1);
        blacklist.setReason(reason);

        addBlacklist(blacklist);
    }

    public void block1069Segment() {
        block1069Segment(null);
    }

    public void block1069Segment(Integer smsType) {
        log.info("执行1069号段一键封禁, smsType={}", smsType);

        List<String> prefixes = Arrays.asList(
                "1069",
                "1068",
                "1065"
        );

        for (String prefix : prefixes) {
            try {
                SmsBlacklist blacklist = new SmsBlacklist();
                blacklist.setMobile(prefix);
                blacklist.setSmsType(smsType);
                blacklist.setIsPrefixMatch(1);
                blacklist.setReason("1069等营销号段一键封禁");
                addBlacklist(blacklist);
                log.info("1069号段封禁成功: prefix={}, smsType={}", prefix, smsType);
            } catch (BusinessException e) {
                log.info("1069号段规则已存在，跳过: prefix={}, smsType={}", prefix, smsType);
            }
        }
    }

    public void unblock1069Segment() {
        unblock1069Segment(null);
    }

    public void unblock1069Segment(Integer smsType) {
        log.info("解除1069号段封禁, smsType={}", smsType);

        List<String> prefixes = Arrays.asList("1069", "1068", "1065");
        for (String prefix : prefixes) {
            removePrefixBlacklist(prefix, smsType);
        }
    }

    public void removeBlacklist(String mobile, Integer smsType) {
        removeBlacklist(mobile, smsType, null);
    }

    public void removeBlacklist(String mobile, Integer smsType, Integer isPrefixMatch) {
        LambdaQueryWrapper<SmsBlacklist> wrapper = new LambdaQueryWrapper<SmsBlacklist>()
                .eq(SmsBlacklist::getMobile, mobile)
                .eq(SmsBlacklist::getDeleted, 0);
        if (smsType != null) {
            wrapper.eq(SmsBlacklist::getSmsType, smsType);
        } else {
            wrapper.isNull(SmsBlacklist::getSmsType);
        }
        if (isPrefixMatch != null) {
            wrapper.eq(SmsBlacklist::getIsPrefixMatch, isPrefixMatch);
        }

        List<SmsBlacklist> toDelete = blacklistMapper.selectList(wrapper);
        for (SmsBlacklist item : toDelete) {
            item.setDeleted(1);
            blacklistMapper.updateById(item);

            String cacheKey;
            if (item.getIsPrefixMatch() == 1) {
                cacheKey = buildPrefixCacheKey(mobile, item.getSmsType());
                prefixBlacklistCache.remove(cacheKey);
            } else {
                cacheKey = buildExactCacheKey(mobile, item.getSmsType());
                exactBlacklistCache.remove(cacheKey);
            }

            removeFromRedis(item);
        }

        log.info("移除黑名单成功: mobile={}, smsType={}, isPrefixMatch={}", mobile, smsType, isPrefixMatch);
    }

    public void removePrefixBlacklist(String prefix, Integer smsType) {
        removeBlacklist(prefix, smsType, 1);
    }

    private void validateBlacklist(SmsBlacklist blacklist) {
        if (blacklist.getMobile() == null || blacklist.getMobile().isEmpty()) {
            throw new BusinessException("手机号或前缀不能为空");
        }

        if (blacklist.getIsPrefixMatch() != null && blacklist.getIsPrefixMatch() == 1) {
            validatePrefix(blacklist.getMobile());
        } else {
            if (!MOBILE_PATTERN.matcher(blacklist.getMobile()).matches()) {
                throw new BusinessException("手机号格式不正确");
            }
        }
    }

    private void validatePrefix(String prefix) {
        if (prefix == null || prefix.isEmpty()) {
            throw new BusinessException("前缀不能为空");
        }
        if (!PREFIX_PATTERN.matcher(prefix).matches()) {
            throw new BusinessException("前缀格式不正确，必须以1开头的有效手机号前缀");
        }
        if (prefix.length() < 3 || prefix.length() > 11) {
            throw new BusinessException("前缀长度必须在3-11位之间");
        }
    }

    private void addToRedis(SmsBlacklist blacklist) {
        String redisKey = buildRedisKey(blacklist);

        if (blacklist.getExpireTime() != null) {
            long ttl = java.time.Duration.between(LocalDateTime.now(), blacklist.getExpireTime()).getSeconds();
            if (ttl > 0) {
                redisUtil.set(redisKey, "1", ttl, TimeUnit.SECONDS);
            }
        } else {
            redisUtil.set(redisKey, "1");
        }
    }

    private void removeFromRedis(SmsBlacklist blacklist) {
        String redisKey = buildRedisKey(blacklist);
        redisUtil.delete(redisKey);
    }

    private String buildRedisKey(SmsBlacklist blacklist) {
        String typePart = blacklist.getSmsType() == null ? "all" : String.valueOf(blacklist.getSmsType());
        if (blacklist.getIsPrefixMatch() != null && blacklist.getIsPrefixMatch() == 1) {
            return BLACKLIST_PREFIX_KEY + blacklist.getMobile() + ":" + typePart;
        } else {
            return BLACKLIST_KEY_PREFIX + EXACT_MATCH_SUFFIX + blacklist.getMobile() + ":" + typePart;
        }
    }

    private boolean isExpired(SmsBlacklist item) {
        if (item.getExpireTime() == null) {
            return false;
        }
        return item.getExpireTime().isBefore(LocalDateTime.now());
    }

    private String buildExactCacheKey(String mobile, Integer smsType) {
        return "E_" + mobile + "_" + (smsType == null ? "all" : smsType);
    }

    private String buildPrefixCacheKey(String prefix, Integer smsType) {
        return "P_" + (smsType == null ? "all" : smsType) + "_" + prefix;
    }

    public List<SmsBlacklist> listBlacklist(String mobile, Integer smsType, Integer isPrefixMatch) {
        LambdaQueryWrapper<SmsBlacklist> wrapper = new LambdaQueryWrapper<SmsBlacklist>()
                .eq(SmsBlacklist::getDeleted, 0)
                .orderByDesc(SmsBlacklist::getCreateTime);
        if (mobile != null && !mobile.isEmpty()) {
            wrapper.eq(SmsBlacklist::getMobile, mobile);
        }
        if (smsType != null) {
            wrapper.eq(SmsBlacklist::getSmsType, smsType);
        }
        if (isPrefixMatch != null) {
            wrapper.eq(SmsBlacklist::getIsPrefixMatch, isPrefixMatch);
        }
        return blacklistMapper.selectList(wrapper);
    }

    public List<SmsBlacklist> listAllPrefixBlacklist() {
        return listBlacklist(null, null, 1);
    }

    public Map<String, Object> getBlacklistStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("exactCount", exactBlacklistCache.size());
        stats.put("prefixCount", prefixBlacklistCache.size());

        List<SmsBlacklist> prefixList = listAllPrefixBlacklist();
        stats.put("prefixRules", prefixList);

        return stats;
    }

    public void refreshCache() {
        exactBlacklistCache.clear();
        prefixBlacklistCache.clear();
        loadBlacklistToCache();
        log.info("黑名单缓存已刷新，精确匹配: {} 条, 前缀匹配: {} 条",
                exactBlacklistCache.size(), prefixBlacklistCache.size());
    }
}

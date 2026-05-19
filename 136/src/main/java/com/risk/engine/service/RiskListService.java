package com.risk.engine.service;

import com.risk.engine.config.RedisConfig.BloomFilterManager;
import com.risk.engine.entity.RiskList;
import com.risk.engine.repository.RiskListRepository;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.PostConstruct;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
@Service
public class RiskListService {

    private static final String REDIS_SET_PREFIX = "risk:list:";
    private static final String BLOOM_FILTER_PREFIX = "bloom:";
    private static final String CACHE_KEY_REGEX_PATTERNS = "risk:regex:patterns";
    private static final long CACHE_EXPIRE_HOURS = 24;

    @Autowired
    private RiskListRepository riskListRepository;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private BloomFilterManager bloomFilterManager;

    private final Map<String, Pattern> regexPatternCache = new HashMap<>();

    @PostConstruct
    public void init() {
        try {
            log.info("开始初始化名单缓存...");
            List<RiskList> activeLists = riskListRepository.findAllActiveLists(LocalDateTime.now());
            loadListsToCache(activeLists);
            log.info("名单缓存初始化完成, 共 {} 条记录", activeLists.size());
        } catch (Exception e) {
            log.error("名单缓存初始化失败", e);
        }
    }

    private void loadListsToCache(List<RiskList> lists) {
        Map<String, Set<String>> setMap = new HashMap<>();
        Map<String, List<RiskList>> regexMap = new HashMap<>();
        Map<String, List<RiskList>> fuzzyMap = new HashMap<>();

        for (RiskList list : lists) {
            String setKey = getSetKey(list.getListType(), list.getMatchType(), list.getFieldName());
            
            if ("EXACT".equals(list.getMatchType())) {
                setMap.computeIfAbsent(setKey, k -> new HashSet<>()).add(list.getFieldValue());
            } else if ("REGEX".equals(list.getMatchType())) {
                regexMap.computeIfAbsent(setKey, k -> new ArrayList<>()).add(list);
            } else if ("FUZZY".equals(list.getMatchType())) {
                fuzzyMap.computeIfAbsent(setKey, k -> new ArrayList<>()).add(list);
            }
        }

        for (Map.Entry<String, Set<String>> entry : setMap.entrySet()) {
            String setKey = entry.getKey();
            Set<String> values = entry.getValue();
            
            redisTemplate.delete(setKey);
            if (!values.isEmpty()) {
                redisTemplate.opsForSet().add(setKey, values.toArray());
                redisTemplate.expire(setKey, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);
            }

            String bloomKey = BLOOM_FILTER_PREFIX + setKey;
            bloomFilterManager.rebuildFilter(bloomKey, values);
            log.debug("加载精确匹配名单: {}, 数量: {}", setKey, values.size());
        }

        regexPatternCache.clear();
        for (Map.Entry<String, List<RiskList>> entry : regexMap.entrySet()) {
            for (RiskList list : entry.getValue()) {
                try {
                    Pattern pattern = Pattern.compile(list.getFieldValue());
                    regexPatternCache.put(list.getId().toString(), pattern);
                } catch (Exception e) {
                    log.warn("正则表达式编译失败: {}", list.getFieldValue());
                }
            }
        }
        log.debug("加载正则匹配名单: {}", regexPatternCache.size());
    }

    private String getSetKey(String listType, String matchType, String fieldName) {
        return REDIS_SET_PREFIX + listType + ":" + matchType + ":" + fieldName;
    }

    public RiskList createList(RiskList riskList) {
        RiskList saved = riskListRepository.save(riskList);
        addToListCache(saved);
        return saved;
    }

    public Optional<RiskList> getListById(Long id) {
        return riskListRepository.findById(id);
    }

    public List<RiskList> getAllLists() {
        return riskListRepository.findAll();
    }

    public List<RiskList> getActiveLists() {
        return riskListRepository.findAllActiveLists(LocalDateTime.now());
    }

    public List<RiskList> getActiveListsByType(String listType) {
        return riskListRepository.findActiveListsByType(listType, LocalDateTime.now());
    }

    @Transactional
    public RiskList updateList(Long id, RiskList riskList) {
        RiskList existingList = riskListRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("名单不存在: " + id));
        
        removeFromListCache(existingList);

        existingList.setListType(riskList.getListType());
        existingList.setMatchType(riskList.getMatchType());
        existingList.setFieldName(riskList.getFieldName());
        existingList.setFieldValue(riskList.getFieldValue());
        existingList.setListDesc(riskList.getListDesc());
        existingList.setStatus(riskList.getStatus());
        existingList.setExpireTime(riskList.getExpireTime());

        RiskList updated = riskListRepository.save(existingList);
        addToListCache(updated);
        return updated;
    }

    @Transactional
    public void deleteList(Long id) {
        RiskList list = riskListRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("名单不存在: " + id));
        riskListRepository.deleteById(id);
        removeFromListCache(list);
    }

    private void addToListCache(RiskList list) {
        if (!"ENABLED".equals(list.getStatus())) {
            return;
        }
        
        String setKey = getSetKey(list.getListType(), list.getMatchType(), list.getFieldName());
        
        if ("EXACT".equals(list.getMatchType())) {
            redisTemplate.opsForSet().add(setKey, list.getFieldValue());
            redisTemplate.expire(setKey, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);
            
            String bloomKey = BLOOM_FILTER_PREFIX + setKey;
            bloomFilterManager.put(bloomKey, list.getFieldValue());
        } else if ("REGEX".equals(list.getMatchType())) {
            try {
                Pattern pattern = Pattern.compile(list.getFieldValue());
                regexPatternCache.put(list.getId().toString(), pattern);
            } catch (Exception e) {
                log.warn("正则表达式编译失败: {}", list.getFieldValue());
            }
        }
    }

    private void removeFromListCache(RiskList list) {
        String setKey = getSetKey(list.getListType(), list.getMatchType(), list.getFieldName());
        
        if ("EXACT".equals(list.getMatchType())) {
            redisTemplate.opsForSet().remove(setKey, list.getFieldValue());
        }
        regexPatternCache.remove(list.getId().toString());
    }

    public List<String> matchLists(Map<String, Object> data, String listType) {
        List<String> matchedLists = new ArrayList<>();

        for (String fieldName : data.keySet()) {
            Object fieldValue = data.get(fieldName);
            if (fieldValue == null) {
                continue;
            }
            String value = String.valueOf(fieldValue);

            matchedLists.addAll(matchExact(listType, fieldName, value));
            matchedLists.addAll(matchFuzzy(listType, fieldName, value));
            matchedLists.addAll(matchRegex(listType, fieldName, value));
        }

        return matchedLists;
    }

    private List<String> matchExact(String listType, String fieldName, String value) {
        List<String> results = new ArrayList<>();
        String setKey = getSetKey(listType, "EXACT", fieldName);

        String bloomKey = BLOOM_FILTER_PREFIX + setKey;
        if (!bloomFilterManager.mightContain(bloomKey, value)) {
            return results;
        }

        Boolean isMember = redisTemplate.opsForSet().isMember(setKey, value);
        if (Boolean.TRUE.equals(isMember)) {
            results.add(listType + ":EXACT:" + fieldName + "=" + value);
        }

        return results;
    }

    private List<String> matchFuzzy(String listType, String fieldName, String value) {
        List<String> results = new ArrayList<>();
        String setKey = getSetKey(listType, "FUZZY", fieldName);

        Set<Object> members = redisTemplate.opsForSet().members(setKey);
        if (members != null) {
            for (Object member : members) {
                String pattern = String.valueOf(member);
                if (StringUtils.contains(value, pattern)) {
                    results.add(listType + ":FUZZY:" + fieldName + "=" + pattern);
                }
            }
        }

        return results;
    }

    private List<String> matchRegex(String listType, String fieldName, String value) {
        List<String> results = new ArrayList<>();
        
        for (Map.Entry<String, Pattern> entry : regexPatternCache.entrySet()) {
            try {
                if (entry.getValue().matcher(value).find()) {
                    results.add(listType + ":REGEX:" + fieldName + "=" + entry.getValue().pattern());
                }
            } catch (Exception e) {
                log.debug("正则匹配异常: {}", e.getMessage());
            }
        }

        return results;
    }

    public boolean isInBlacklist(Map<String, Object> data) {
        return !matchLists(data, "BLACKLIST").isEmpty();
    }

    public boolean isInWhitelist(Map<String, Object> data) {
        return !matchLists(data, "WHITELIST").isEmpty();
    }

    public void reloadCache() {
        log.info("开始重新加载名单缓存...");
        List<RiskList> activeLists = riskListRepository.findAllActiveLists(LocalDateTime.now());
        loadListsToCache(activeLists);
        log.info("名单缓存重新加载完成, 共 {} 条记录", activeLists.size());
    }
}

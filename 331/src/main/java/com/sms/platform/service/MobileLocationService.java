package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sms.platform.common.enums.MobileOperatorEnum;
import com.sms.platform.entity.SmsMobileLocation;
import com.sms.platform.mapper.SmsMobileLocationMapper;
import com.sms.platform.util.RedisUtil;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class MobileLocationService {

    @Resource
    private SmsMobileLocationMapper locationMapper;

    @Resource
    private SmsMobileLocationMapper mobileLocationMapper;

    @Resource
    private RedisUtil redisUtil;

    private static final String LOCATION_CACHE_PREFIX = "sms:mobile:location:";

    private final Map<String, SmsMobileLocation> locationCache = new ConcurrentHashMap<>();

    private static final Map<String, MobileOperatorEnum> OPERATOR_PREFIX_MAP = new HashMap<>();
    static {
        String[] chinaMobile = {"134", "135", "136", "137", "138", "139", "150", "151", "152", "157", "158", "159",
                "182", "183", "184", "187", "188", "178", "147", "172", "198", "195", "1705", "1340", "1341"};
        String[] chinaUnicom = {"130", "131", "132", "155", "156", "185", "186", "175", "176", "145",
                "1704", "1707", "1708", "1709", "171", "166", "196"};
        String[] chinaTelecom = {"133", "153", "180", "181", "189", "177", "173", "199", "191", "190",
                "1700", "1701", "1702", "1349", "1410", "162", "167"};

        for (String prefix : chinaMobile) {
            OPERATOR_PREFIX_MAP.put(prefix, MobileOperatorEnum.CHINA_MOBILE);
        }
        for (String prefix : chinaUnicom) {
            OPERATOR_PREFIX_MAP.put(prefix, MobileOperatorEnum.CHINA_UNICOM);
        }
        for (String prefix : chinaTelecom) {
            OPERATOR_PREFIX_MAP.put(prefix, MobileOperatorEnum.CHINA_TELECOM);
        }
    }

    @PostConstruct
    public void init() {
        loadLocationCache();
        log.info("号码归属地服务初始化完成，共加载 {} 条号段数据", locationCache.size());
    }

    private void loadLocationCache() {
        List<SmsMobileLocation> locations = locationMapper.selectList(
                new LambdaQueryWrapper<SmsMobileLocation>()
                        .eq(SmsMobileLocation::getDeleted, 0)
        );

        for (SmsMobileLocation location : locations) {
            locationCache.put(location.getMobilePrefix(), location);
        }
    }

    public MobileLocationInfo analyzeMobile(String mobile) {
        MobileLocationInfo info = new MobileLocationInfo();
        info.setMobile(mobile);

        if (mobile == null || mobile.length() < 7) {
            info.setValid(false);
            info.setOperator(MobileOperatorEnum.OTHER.getCode());
            info.setOperatorName(MobileOperatorEnum.OTHER.getName());
            return info;
        }

        info.setValid(true);
        String prefix7 = mobile.substring(0, 7);
        String prefix3 = mobile.substring(0, 3);
        String prefix4 = mobile.length() >= 4 ? mobile.substring(0, 4) : prefix3;

        SmsMobileLocation location = locationCache.get(prefix7);
        if (location == null) {
            location = queryFromCacheOrDb(mobile, prefix7);
        }

        if (location != null) {
            info.setProvince(location.getProvince());
            info.setCity(location.getCity());
            info.setOperator(location.getOperator());
            info.setOperatorName(getOperatorName(location.getOperator()));
            info.setMatchedPrefix(location.getMobilePrefix());
            info.setSource("DB");
        } else {
            MobileOperatorEnum operator = detectOperator(prefix3, prefix4);
            info.setOperator(operator.getCode());
            info.setOperatorName(operator.getName());
            info.setProvince("未知");
            info.setCity("未知");
            info.setMatchedPrefix(prefix3);
            info.setSource("规则匹配");
        }

        saveToRedis(mobile, info);

        return info;
    }

    private SmsMobileLocation queryFromCacheOrDb(String mobile, String prefix7) {
        String redisKey = LOCATION_CACHE_PREFIX + prefix7;
        try {
            Object cached = redisUtil.hGet(redisKey, "province");
            if (cached != null) {
                SmsMobileLocation location = new SmsMobileLocation();
                location.setMobilePrefix(prefix7);
                location.setProvince(String.valueOf(cached));
                Object city = redisUtil.hGet(redisKey, "city");
                Object operator = redisUtil.hGet(redisKey, "operator");
                if (city != null) location.setCity(String.valueOf(city));
                if (operator != null) location.setOperator(Integer.parseInt(String.valueOf(operator)));
                locationCache.put(prefix7, location);
                return location;
            }
        } catch (Exception e) {
            log.debug("从Redis查询归属地失败", e);
        }

        SmsMobileLocation location = locationMapper.selectOne(
                new LambdaQueryWrapper<SmsMobileLocation>()
                        .likeRight(SmsMobileLocation::getMobilePrefix, prefix7)
                        .eq(SmsMobileLocation::getDeleted, 0)
                        .last("LIMIT 1")
        );

        if (location != null) {
            locationCache.put(location.getMobilePrefix(), location);
            try {
                Map<String, Object> data = new HashMap<>();
                data.put("province", location.getProvince());
                data.put("city", location.getCity());
                data.put("operator", location.getOperator());
                redisUtil.hSetAll(LOCATION_CACHE_PREFIX + location.getMobilePrefix(), data);
                redisUtil.expire(LOCATION_CACHE_PREFIX + location.getMobilePrefix(), 24, TimeUnit.HOURS);
            } catch (Exception e) {
                log.debug("缓存归属地到Redis失败", e);
            }
        }

        return location;
    }

    private MobileOperatorEnum detectOperator(String prefix3, String prefix4) {
        MobileOperatorEnum operator = OPERATOR_PREFIX_MAP.get(prefix4);
        if (operator != null) {
            return operator;
        }

        operator = OPERATOR_PREFIX_MAP.get(prefix3);
        if (operator != null) {
            return operator;
        }

        return MobileOperatorEnum.OTHER;
    }

    private String getOperatorName(Integer operatorCode) {
        MobileOperatorEnum operator = MobileOperatorEnum.getByCode(operatorCode);
        return operator != null ? operator.getName() : "其他";
    }

    private void saveToRedis(String mobile, MobileLocationInfo info) {
        try {
            String key = LOCATION_CACHE_PREFIX + mobile;
            Map<String, Object> data = new HashMap<>();
            data.put("province", info.getProvince());
            data.put("city", info.getCity());
            data.put("operator", info.getOperator());
            data.put("operatorName", info.getOperatorName());
            redisUtil.hSetAll(key, data);
            redisUtil.expire(key, 24, TimeUnit.HOURS);
        } catch (Exception e) {
            log.debug("缓存手机号归属地到Redis失败", e);
        }
    }

    public List<Map<String, Object>> getProvinceStatistics(LocalDate startDate, LocalDate endDate) {
        LocalDateTime startTime = startDate != null ? startDate.atStartOfDay() : LocalDate.now().atStartOfDay();
        LocalDateTime endTime = endDate != null ? endDate.atTime(LocalTime.MAX) : LocalDate.now().atTime(LocalTime.MAX);

        List<Map<String, Object>> stats = mobileLocationMapper.selectStatisticsByProvince(startTime, endTime);

        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> stat : stats) {
            Map<String, Object> item = new HashMap<>(stat);
            long total = ((Number) stat.get("total")).longValue();
            long successCount = ((Number) stat.get("successCount")).longValue();
            double successRate = total > 0 ? (successCount * 100.0 / total) : 0;
            item.put("successRate", String.format("%.2f%%", successRate));
            result.add(item);
        }

        result.sort((a, b) -> Long.compare(((Number) b.get("total")).longValue(), ((Number) a.get("total")).longValue()));
        return result;
    }

    public List<Map<String, Object>> getOperatorStatistics(LocalDate startDate, LocalDate endDate) {
        LocalDateTime startTime = startDate != null ? startDate.atStartOfDay() : LocalDate.now().atStartOfDay();
        LocalDateTime endTime = endDate != null ? endDate.atTime(LocalTime.MAX) : LocalDate.now().atTime(LocalTime.MAX);

        List<Map<String, Object>> stats = mobileLocationMapper.selectStatisticsByOperator(startTime, endTime);

        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> stat : stats) {
            Map<String, Object> item = new HashMap<>(stat);
            long total = ((Number) stat.get("total")).longValue();
            long successCount = ((Number) stat.get("successCount")).longValue();
            double successRate = total > 0 ? (successCount * 100.0 / total) : 0;
            item.put("successRate", String.format("%.2f%%", successRate));

            Integer operatorCode = ((Number) stat.get("operator")).intValue();
            MobileOperatorEnum operator = MobileOperatorEnum.getByCode(operatorCode);
            item.put("operatorName", operator != null ? operator.getName() : "其他");

            result.add(item);
        }

        result.sort((a, b) -> Long.compare(((Number) b.get("total")).longValue(), ((Number) a.get("total")).longValue()));
        return result;
    }

    public Map<String, Object> getFullStatistics(LocalDate startDate, LocalDate endDate) {
        Map<String, Object> result = new HashMap<>();
        result.put("byProvince", getProvinceStatistics(startDate, endDate));
        result.put("byOperator", getOperatorStatistics(startDate, endDate));
        return result;
    }

    public void addLocation(SmsMobileLocation location) {
        LambdaQueryWrapper<SmsMobileLocation> existsWrapper = new LambdaQueryWrapper<SmsMobileLocation>()
                .eq(SmsMobileLocation::getMobilePrefix, location.getMobilePrefix())
                .eq(SmsMobileLocation::getDeleted, 0);
        if (locationMapper.selectOne(existsWrapper) != null) {
            throw new com.sms.platform.common.exception.BusinessException("该号段已存在");
        }

        locationMapper.insert(location);
        locationCache.put(location.getMobilePrefix(), location);
        log.info("添加号段归属地成功: {} - {} {}", location.getMobilePrefix(), location.getProvince(), location.getCity());
    }

    public void addLocationBatch(List<SmsMobileLocation> locations) {
        for (SmsMobileLocation location : locations) {
            try {
                addLocation(location);
            } catch (Exception e) {
                log.warn("批量添加号段跳过已存在的号段: {}", location.getMobilePrefix());
            }
        }
    }

    public void deleteLocation(Long id) {
        SmsMobileLocation location = locationMapper.selectById(id);
        if (location != null && location.getDeleted() == 0) {
            location.setDeleted(1);
            locationMapper.updateById(location);
            locationCache.remove(location.getMobilePrefix());
            log.info("删除号段归属地成功: {}", location.getMobilePrefix());
        }
    }

    public List<SmsMobileLocation> listLocations(String province, Integer operator) {
        LambdaQueryWrapper<SmsMobileLocation> wrapper = new LambdaQueryWrapper<SmsMobileLocation>()
                .eq(SmsMobileLocation::getDeleted, 0)
                .orderByAsc(SmsMobileLocation::getMobilePrefix);

        if (province != null && !province.isEmpty()) {
            wrapper.eq(SmsMobileLocation::getProvince, province);
        }
        if (operator != null) {
            wrapper.eq(SmsMobileLocation::getOperator, operator);
        }

        return locationMapper.selectList(wrapper);
    }

    public void refreshCache() {
        locationCache.clear();
        loadLocationCache();
        log.info("号码归属地缓存已刷新，共 {} 条", locationCache.size());
    }

    @Data
    public static class MobileLocationInfo {
        private boolean valid;
        private String mobile;
        private String province;
        private String city;
        private Integer operator;
        private String operatorName;
        private String matchedPrefix;
        private String source;
    }
}

package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sms.platform.common.exception.BusinessException;
import com.sms.platform.entity.SmsSendTimePolicy;
import com.sms.platform.mapper.SmsSendTimePolicyMapper;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class SendTimePolicyService {

    @Resource
    private SmsSendTimePolicyMapper policyMapper;

    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("HH:mm");

    private final Map<Integer, List<SmsSendTimePolicy>> policyBySmsTypeCache = new ConcurrentHashMap<>();
    private final List<SmsSendTimePolicy> allTypePolicyCache = new ArrayList<>();
    private volatile long lastRefreshTime = 0;
    private static final long CACHE_REFRESH_INTERVAL = 60000;

    @PostConstruct
    public void init() {
        refreshPolicyCache();
        log.info("发送时段策略服务初始化完成，共加载 {} 条策略",
                allTypePolicyCache.size() + policyBySmsTypeCache.values().stream().mapToInt(List::size).sum());
    }

    public TimeCheckResult checkSendAllowed(Integer smsType) {
        return checkSendAllowed(smsType, LocalDateTime.now());
    }

    public TimeCheckResult checkSendAllowed(Integer smsType, LocalDateTime sendTime) {
        ensureCacheFresh();

        List<SmsSendTimePolicy> applicablePolicies = new ArrayList<>();

        if (allTypePolicyCache != null && !allTypePolicyCache.isEmpty()) {
            applicablePolicies.addAll(allTypePolicyCache);
        }

        if (smsType != null && policyBySmsTypeCache.containsKey(smsType)) {
            applicablePolicies.addAll(policyBySmsTypeCache.get(smsType));
        }

        if (applicablePolicies.isEmpty()) {
            TimeCheckResult result = new TimeCheckResult();
            result.setAllowed(true);
            result.setReason("无限制策略，允许发送");
            return result;
        }

        applicablePolicies.sort(Comparator.comparing(p -> p.getSmsType() == null ? 1 : 0));

        for (SmsSendTimePolicy policy : applicablePolicies) {
            if (policy.getStatus() != 1) {
                continue;
            }

            if (!isWeekdayAllowed(policy.getWeekdays(), sendTime)) {
                continue;
            }

            ZoneId zoneId = getZoneId(policy.getTimezone());
            ZonedDateTime zonedTime = sendTime.atZone(ZoneId.systemDefault()).withZoneSameInstant(zoneId);
            LocalTime localTime = zonedTime.toLocalTime();

            LocalTime startTime = LocalTime.parse(policy.getTimeStart(), TIME_FORMATTER);
            LocalTime endTime = LocalTime.parse(policy.getTimeEnd(), TIME_FORMATTER);

            boolean withinTime = !localTime.isBefore(startTime) && !localTime.isAfter(endTime);

            if (withinTime) {
                TimeCheckResult result = new TimeCheckResult();
                result.setAllowed(true);
                result.setPolicyId(policy.getId());
                result.setPolicyName(policy.getPolicyName());
                result.setTimeStart(policy.getTimeStart());
                result.setTimeEnd(policy.getTimeEnd());
                result.setReason("符合时段策略: " + policy.getPolicyName());
                return result;
            }
        }

        TimeCheckResult result = new TimeCheckResult();
        result.setAllowed(false);
        result.setReason("不在允许的发送时段内，请在允许的时段内发送");

        for (SmsSendTimePolicy policy : applicablePolicies) {
            if (policy.getStatus() == 1) {
                result.setPolicyName(policy.getPolicyName());
                result.setTimeStart(policy.getTimeStart());
                result.setTimeEnd(policy.getTimeEnd());
                result.setPolicyId(policy.getId());
                break;
            }
        }

        log.warn("发送时段限制, smsType={}, sendTime={}, reason={}", smsType, sendTime, result.getReason());
        return result;
    }

    private boolean isWeekdayAllowed(String weekdays, LocalDateTime sendTime) {
        if (weekdays == null || weekdays.isEmpty()) {
            return true;
        }

        try {
            DayOfWeek dayOfWeek = sendTime.getDayOfWeek();
            int dayValue = dayOfWeek.getValue();

            String[] allowedDays = weekdays.split(",");
            for (String day : allowedDays) {
                if (String.valueOf(dayValue).equals(day.trim())) {
                    return true;
                }
            }
            return false;
        } catch (Exception e) {
            log.error("检查星期限制失败", e);
            return true;
        }
    }

    private ZoneId getZoneId(String timezone) {
        if (timezone == null || timezone.isEmpty()) {
            return ZoneId.of("Asia/Shanghai");
        }
        try {
            return ZoneId.of(timezone);
        } catch (Exception e) {
            log.warn("无效的时区: {}, 使用默认时区", timezone);
            return ZoneId.of("Asia/Shanghai");
        }
    }

    public void addPolicy(SmsSendTimePolicy policy) {
        validatePolicy(policy);

        LambdaQueryWrapper<SmsSendTimePolicy> existsWrapper = new LambdaQueryWrapper<SmsSendTimePolicy>()
                .eq(SmsSendTimePolicy::getSmsType, policy.getSmsType())
                .eq(SmsSendTimePolicy::getDeleted, 0);
        if (policy.getSmsType() == null) {
            existsWrapper.isNull(SmsSendTimePolicy::getSmsType);
        }

        if (policyMapper.selectOne(existsWrapper) != null) {
            throw new BusinessException("该短信类型的时段策略已存在");
        }

        policyMapper.insert(policy);
        refreshPolicyCache();
        log.info("添加时段策略成功: {}, smsType={}", policy.getPolicyName(), policy.getSmsType());
    }

    public void updatePolicy(SmsSendTimePolicy policy) {
        SmsSendTimePolicy exists = policyMapper.selectById(policy.getId());
        if (exists == null || exists.getDeleted() == 1) {
            throw new BusinessException("时段策略不存在");
        }
        validatePolicy(policy);
        policyMapper.updateById(policy);
        refreshPolicyCache();
        log.info("更新时段策略成功: id={}", policy.getId());
    }

    public void deletePolicy(Long id) {
        SmsSendTimePolicy policy = policyMapper.selectById(id);
        if (policy == null || policy.getDeleted() == 1) {
            throw new BusinessException("时段策略不存在");
        }
        policy.setDeleted(1);
        policyMapper.updateById(policy);
        refreshPolicyCache();
        log.info("删除时段策略成功: id={}, name={}", id, policy.getPolicyName());
    }

    public SmsSendTimePolicy getPolicy(Long id) {
        SmsSendTimePolicy policy = policyMapper.selectById(id);
        if (policy == null || policy.getDeleted() == 1) {
            throw new BusinessException("时段策略不存在");
        }
        return policy;
    }

    public List<SmsSendTimePolicy> listPolicies() {
        return policyMapper.selectList(
                new LambdaQueryWrapper<SmsSendTimePolicy>()
                        .eq(SmsSendTimePolicy::getDeleted, 0)
                        .orderByAsc(SmsSendTimePolicy::getSmsType)
        );
    }

    private void validatePolicy(SmsSendTimePolicy policy) {
        if (policy.getTimeStart() == null || policy.getTimeEnd() == null) {
            throw new BusinessException("时间段不能为空");
        }

        try {
            LocalTime.parse(policy.getTimeStart(), TIME_FORMATTER);
            LocalTime.parse(policy.getTimeEnd(), TIME_FORMATTER);
        } catch (Exception e) {
            throw new BusinessException("时间格式不正确，请使用HH:mm格式");
        }

        if (policy.getWeekdays() != null && !policy.getWeekdays().isEmpty()) {
            String[] days = policy.getWeekdays().split(",");
            for (String day : days) {
                try {
                    int d = Integer.parseInt(day.trim());
                    if (d < 1 || d > 7) {
                        throw new BusinessException("星期值必须在1-7之间");
                    }
                } catch (NumberFormatException e) {
                    throw new BusinessException("星期格式不正确，请使用逗号分隔的数字，如1,2,3,4,5");
                }
            }
        }
    }

    private synchronized void refreshPolicyCache() {
        List<SmsSendTimePolicy> allPolicies = policyMapper.selectList(
                new LambdaQueryWrapper<SmsSendTimePolicy>()
                        .eq(SmsSendTimePolicy::getStatus, 1)
                        .eq(SmsSendTimePolicy::getDeleted, 0)
        );

        policyBySmsTypeCache.clear();
        allTypePolicyCache.clear();

        for (SmsSendTimePolicy policy : allPolicies) {
            if (policy.getSmsType() == null) {
                allTypePolicyCache.add(policy);
            } else {
                policyBySmsTypeCache
                        .computeIfAbsent(policy.getSmsType(), k -> new ArrayList<>())
                        .add(policy);
            }
        }

        lastRefreshTime = System.currentTimeMillis();
        log.info("时段策略缓存已刷新, 全局策略: {} 条, 分类型策略: {} 条",
                allTypePolicyCache.size(), policyBySmsTypeCache.size());
    }

    private void ensureCacheFresh() {
        if (System.currentTimeMillis() - lastRefreshTime > CACHE_REFRESH_INTERVAL) {
            refreshPolicyCache();
        }
    }

    public void refreshCache() {
        refreshPolicyCache();
    }

    public Map<String, Object> getPolicyStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("allTypePolicyCount", allTypePolicyCache.size());
        status.put("typedPolicyCount", policyBySmsTypeCache.size());
        status.put("lastRefreshTime", new Date(lastRefreshTime));

        Map<Integer, String> currentTimeByType = new HashMap<>();
        for (Integer smsType : Arrays.asList(1, 2, 3)) {
            TimeCheckResult result = checkSendAllowed(smsType);
            currentTimeByType.put(smsType, result.isAllowed() ? "允许" : "禁止");
        }
        status.put("currentStatusByType", currentTimeByType);

        return status;
    }

    @Data
    public static class TimeCheckResult {
        private boolean allowed;
        private Long policyId;
        private String policyName;
        private String timeStart;
        private String timeEnd;
        private String reason;
    }
}

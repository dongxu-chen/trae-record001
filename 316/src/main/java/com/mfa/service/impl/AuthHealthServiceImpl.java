package com.mfa.service.impl;

import com.mfa.dto.AuthHealthDashboard;
import com.mfa.dto.AuthMethodStats;
import com.mfa.dto.DailyTrendData;
import com.mfa.entity.AuthLog;
import com.mfa.enums.AuthStatus;
import com.mfa.enums.FactorType;
import com.mfa.repository.AuthLogRepository;
import com.mfa.repository.UserRepository;
import com.mfa.service.AuthHealthService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthHealthServiceImpl implements AuthHealthService {

    private final AuthLogRepository authLogRepository;
    private final UserRepository userRepository;

    private static final Map<FactorType, String> METHOD_NAMES = new EnumMap<>(FactorType.class);

    static {
        METHOD_NAMES.put(FactorType.SMS, "短信验证码");
        METHOD_NAMES.put(FactorType.EMAIL, "邮件验证码");
        METHOD_NAMES.put(FactorType.TOTP, "TOTP验证码");
        METHOD_NAMES.put(FactorType.WEBAUTHN, "Passkey/WebAuthn");
        METHOD_NAMES.put(FactorType.FINGERPRINT, "指纹识别");
        METHOD_NAMES.put(FactorType.FACE, "人脸识别");
        METHOD_NAMES.put(FactorType.VOICE, "声纹识别");
    }

    @Override
    public AuthHealthDashboard getDashboard() {
        LocalDate today = LocalDate.now();
        return getDashboardForDateRange(today.minusDays(6), today);
    }

    @Override
    public List<AuthMethodStats> getAuthMethodStats(LocalDate startDate, LocalDate endDate) {
        LocalDateTime start = startDate.atStartOfDay();
        LocalDateTime end = endDate.plusDays(1).atStartOfDay();

        List<Object[]> results = authLogRepository.countByFactorTypeAndStatusAndCreatedAtBetween(start, end);

        Map<FactorType, long[]> methodCounts = new EnumMap<>(FactorType.class);
        long totalAttempts = 0;

        for (Object[] result : results) {
            FactorType factorType = (FactorType) result[0];
            AuthStatus status = (AuthStatus) result[1];
            Long count = (Long) result[2];

            if (factorType == null) continue;

            methodCounts.computeIfAbsent(factorType, k -> new long[2]);
            if (status == AuthStatus.SUCCESS) {
                methodCounts.get(factorType)[0] += count;
            } else if (status == AuthStatus.FAILED) {
                methodCounts.get(factorType)[1] += count;
            }
            totalAttempts += count;
        }

        final long finalTotalAttempts = totalAttempts;
        return methodCounts.entrySet().stream()
                .map(entry -> {
                    FactorType method = entry.getKey();
                    long[] counts = entry.getValue();
                    long success = counts[0];
                    long failure = counts[1];
                    long total = success + failure;

                    BigDecimal successRate = total > 0
                            ? BigDecimal.valueOf(success * 100.0 / total).setScale(2, RoundingMode.HALF_UP)
                            : BigDecimal.ZERO;
                    BigDecimal usagePercentage = finalTotalAttempts > 0
                            ? BigDecimal.valueOf(total * 100.0 / finalTotalAttempts).setScale(2, RoundingMode.HALF_UP)
                            : BigDecimal.ZERO;

                    return AuthMethodStats.builder()
                            .method(method.name())
                            .methodName(METHOD_NAMES.getOrDefault(method, method.name()))
                            .totalAttempts(total)
                            .successCount(success)
                            .failureCount(failure)
                            .successRate(successRate)
                            .usagePercentage(usagePercentage)
                            .avgResponseTimeMs(generateAvgResponseTime(method))
                            .build();
                })
                .sorted((a, b) -> Long.compare(b.getTotalAttempts(), a.getTotalAttempts()))
                .collect(Collectors.toList());
    }

    @Override
    public AuthHealthDashboard getDashboardForDateRange(LocalDate startDate, LocalDate endDate) {
        LocalDateTime start = startDate.atStartOfDay();
        LocalDateTime end = endDate.plusDays(1).atStartOfDay();
        LocalDateTime todayStart = LocalDate.now().atStartOfDay();
        LocalDateTime todayEnd = LocalDate.now().plusDays(1).atStartOfDay();

        long totalUsers = userRepository.count();
        long activeUsersToday = authLogRepository.countDistinctUsersByCreatedAtBetween(todayStart, todayEnd);
        long totalAttemptsToday = authLogRepository.countByCreatedAtBetween(todayStart, todayEnd);
        long successCountToday = authLogRepository.countByStatusAndCreatedAtBetween(AuthStatus.SUCCESS, todayStart, todayEnd);
        long failureCountToday = authLogRepository.countByStatusAndCreatedAtBetween(AuthStatus.FAILED, todayStart, todayEnd);

        BigDecimal overallSuccessRate = totalAttemptsToday > 0
                ? BigDecimal.valueOf(successCountToday * 100.0 / totalAttemptsToday).setScale(2, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

        List<AuthMethodStats> methodStats = getAuthMethodStats(startDate, endDate);
        List<DailyTrendData> dailyTrends = getDailyTrends(startDate, endDate);
        Map<String, Long> riskLevelDistribution = getRiskLevelDistribution(start, end);
        Map<String, Long> failureReasons = getFailureReasons(start, end);

        return AuthHealthDashboard.builder()
                .totalUsers(totalUsers)
                .activeUsersToday(activeUsersToday)
                .totalAttemptsToday(totalAttemptsToday)
                .successCountToday(successCountToday)
                .failureCountToday(failureCountToday)
                .overallSuccessRate(overallSuccessRate)
                .methodStats(methodStats)
                .dailyTrends(dailyTrends)
                .riskLevelDistribution(riskLevelDistribution)
                .failureReasons(failureReasons)
                .avgAuthenticationTimeMs(BigDecimal.valueOf(850))
                .reportDate(LocalDate.now())
                .build();
    }

    private List<DailyTrendData> getDailyTrends(LocalDate startDate, LocalDate endDate) {
        LocalDateTime start = startDate.atStartOfDay();
        LocalDateTime end = endDate.plusDays(1).atStartOfDay();

        List<Object[]> results = authLogRepository.countByDateAndStatusAndCreatedAtBetween(start, end);

        Map<LocalDate, long[]> dailyCounts = new LinkedHashMap<>();
        LocalDate current = startDate;
        while (!current.isAfter(endDate)) {
            dailyCounts.put(current, new long[2]);
            current = current.plusDays(1);
        }

        for (Object[] result : results) {
            java.sql.Date sqlDate = (java.sql.Date) result[0];
            LocalDate date = sqlDate.toLocalDate();
            AuthStatus status = (AuthStatus) result[1];
            Long count = (Long) result[2];

            if (dailyCounts.containsKey(date)) {
                if (status == AuthStatus.SUCCESS) {
                    dailyCounts.get(date)[0] += count;
                } else if (status == AuthStatus.FAILED) {
                    dailyCounts.get(date)[1] += count;
                }
            }
        }

        return dailyCounts.entrySet().stream()
                .map(entry -> {
                    LocalDate date = entry.getKey();
                    long[] counts = entry.getValue();
                    long success = counts[0];
                    long failure = counts[1];
                    long total = success + failure;

                    BigDecimal successRate = total > 0
                            ? BigDecimal.valueOf(success * 100.0 / total).setScale(2, RoundingMode.HALF_UP)
                            : BigDecimal.ZERO;

                    return DailyTrendData.builder()
                            .date(date)
                            .totalAttempts(total)
                            .successCount(success)
                            .failureCount(failure)
                            .successRate(successRate)
                            .build();
                })
                .collect(Collectors.toList());
    }

    private Map<String, Long> getRiskLevelDistribution(LocalDateTime start, LocalDateTime end) {
        List<Object[]> results = authLogRepository.countByRiskLevelAndCreatedAtBetween(start, end);
        Map<String, Long> distribution = new LinkedHashMap<>();

        String[] order = {"LOW", "MEDIUM", "HIGH", "CRITICAL"};
        for (String level : order) {
            distribution.put(level, 0L);
        }

        for (Object[] result : results) {
            String level = (String) result[0];
            Long count = (Long) result[1];
            if (level != null) {
                distribution.put(level, count);
            }
        }

        return distribution;
    }

    private Map<String, Long> getFailureReasons(LocalDateTime start, LocalDateTime end) {
        List<Object[]> results = authLogRepository.countFailureReasonsByCreatedAtBetween(start, end);
        Map<String, Long> reasons = new LinkedHashMap<>();

        for (Object[] result : results) {
            String message = (String) result[0];
            Long count = (Long) result[1];
            if (message != null && count > 0) {
                String simplifiedReason = simplifyFailureReason(message);
                reasons.merge(simplifiedReason, count, Long::sum);
            }
        }

        return reasons.entrySet().stream()
                .sorted((a, b) -> Long.compare(b.getValue(), a.getValue()))
                .limit(10)
                .collect(Collectors.toMap(
                        Map.Entry::getKey,
                        Map.Entry::getValue,
                        (e1, e2) -> e1,
                        LinkedHashMap::new
                ));
    }

    private String simplifyFailureReason(String message) {
        if (message.contains("密码") || message.contains("password")) {
            return "密码错误";
        } else if (message.contains("验证码") || message.contains("code")) {
            return "验证码错误";
        } else if (message.contains("TOTP") || message.contains("totp")) {
            return "TOTP验证失败";
        } else if (message.contains("WebAuthn") || message.contains("Passkey")) {
            return "Passkey验证失败";
        } else if (message.contains("生物") || message.contains("biometric") || message.contains("指纹") || message.contains("人脸")) {
            return "生物识别失败";
        } else if (message.contains("锁定") || message.contains("locked")) {
            return "账号已锁定";
        } else if (message.contains("禁用") || message.contains("disabled")) {
            return "账号已禁用";
        } else if (message.contains("过期") || message.contains("expired")) {
            return "会话已过期";
        } else if (message.contains("风险") || message.contains("risk")) {
            return "风险评估拦截";
        } else {
            return "其他原因";
        }
    }

    private Long generateAvgResponseTime(FactorType method) {
        return switch (method) {
            case SMS -> 1500L;
            case EMAIL -> 2000L;
            case TOTP -> 300L;
            case WEBAUTHN -> 400L;
            case FINGERPRINT, FACE, VOICE -> 600L;
        };
    }
}

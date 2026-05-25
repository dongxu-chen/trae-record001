package com.coupon.redis.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class CouponStockService {

    private static final String STOCK_KEY_PREFIX = "coupon:stock:";
    private static final String USER_ISSUE_KEY_PREFIX = "coupon:user:issue:";
    private static final String DAILY_BUDGET_KEY = "budget:daily:";
    private static final String DAILY_COUPON_COUNT_KEY = "coupon:daily:count:";

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    private final StringRedisTemplate redisTemplate;

    @Value("${coupon.cache.coupon-stock-ttl:600}")
    private long stockTtlSeconds;

    @Value("${coupon.budget.daily-budget:100000}")
    private long dailyBudget;

    @Value("${coupon.budget.max-coupons-per-day:5000}")
    private long maxCouponsPerDay;

    private final DefaultRedisScript<Long> deductStockScript;

    public CouponStockService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;

        this.deductStockScript = new DefaultRedisScript<>();
        this.deductStockScript.setScriptText(
                "local stock = tonumber(redis.call('GET', KEYS[1]))\n" +
                "if stock == nil or stock <= 0 then\n" +
                "    return -1\n" +
                "end\n" +
                "if stock >= tonumber(ARGV[1]) then\n" +
                "    redis.call('DECRBY', KEYS[1], ARGV[1])\n" +
                "    return tonumber(ARGV[1])\n" +
                "end\n" +
                "return -1"
        );
        this.deductStockScript.setResultType(Long.class);
    }

    public void initStock(String couponId, int stock) {
        String key = getStockKey(couponId);
        try {
            redisTemplate.opsForValue().set(key, String.valueOf(stock), stockTtlSeconds, TimeUnit.SECONDS);
            log.info("Initialized stock for coupon {}: {}", couponId, stock);
        } catch (Exception e) {
            log.error("Failed to initialize stock for coupon: {}", couponId, e);
        }
    }

    public boolean deductStock(String couponId, int quantity) {
        String key = getStockKey(couponId);
        try {
            Long result = redisTemplate.execute(
                    deductStockScript,
                    Collections.singletonList(key),
                    String.valueOf(quantity)
            );
            boolean success = result != null && result > 0;
            if (success) {
                log.debug("Deducted stock for coupon {}: {}", couponId, quantity);
            } else {
                log.warn("Insufficient stock for coupon {}", couponId);
            }
            return success;
        } catch (Exception e) {
            log.error("Failed to deduct stock for coupon: {}", couponId, e);
            return false;
        }
    }

    public boolean deductStock(String couponId) {
        return deductStock(couponId, 1);
    }

    public void returnStock(String couponId, int quantity) {
        String key = getStockKey(couponId);
        try {
            redisTemplate.opsForValue().increment(key, quantity);
            log.debug("Returned stock for coupon {}: {}", couponId, quantity);
        } catch (Exception e) {
            log.error("Failed to return stock for coupon: {}", couponId, e);
        }
    }

    public int getStock(String couponId) {
        String key = getStockKey(couponId);
        try {
            String stockStr = redisTemplate.opsForValue().get(key);
            if (stockStr != null) {
                return Integer.parseInt(stockStr);
            }
        } catch (Exception e) {
            log.error("Failed to get stock for coupon: {}", couponId, e);
        }
        return 0;
    }

    public boolean checkAndConsumeDailyBudget(double amount) {
        String key = getDailyBudgetKey();
        try {
            String currentStr = redisTemplate.opsForValue().get(key);
            double currentSpent = currentStr != null ? Double.parseDouble(currentStr) : 0;

            if (currentSpent + amount > dailyBudget) {
                log.warn("Daily budget exceeded: current={}, amount={}, budget={}",
                        currentSpent, amount, dailyBudget);
                return false;
            }

            redisTemplate.opsForValue().increment(key, amount);
            redisTemplate.expire(key, 1, TimeUnit.DAYS);
            log.debug("Consumed daily budget: amount={}, total={}", amount, currentSpent + amount);
            return true;
        } catch (Exception e) {
            log.error("Failed to check and consume daily budget", e);
            return false;
        }
    }

    public boolean checkDailyCouponLimit() {
        String key = getDailyCouponCountKey();
        try {
            Long current = redisTemplate.opsForValue().increment(key);
            if (current != null && current > maxCouponsPerDay) {
                redisTemplate.opsForValue().decrement(key);
                log.warn("Daily coupon limit exceeded: current={}, max={}",
                        current, maxCouponsPerDay);
                return false;
            }
            if (current != null && current == 1) {
                redisTemplate.expire(key, 1, TimeUnit.DAYS);
            }
            return true;
        } catch (Exception e) {
            log.error("Failed to check daily coupon limit", e);
            return true;
        }
    }

    public void releaseDailyBudget(double amount) {
        String key = getDailyBudgetKey();
        try {
            redisTemplate.opsForValue().decrement(key, amount);
            log.debug("Released daily budget: {}", amount);
        } catch (Exception e) {
            log.error("Failed to release daily budget", e);
        }
    }

    public double getDailyBudgetUsed() {
        String key = getDailyBudgetKey();
        try {
            String currentStr = redisTemplate.opsForValue().get(key);
            return currentStr != null ? Double.parseDouble(currentStr) : 0;
        } catch (Exception e) {
            log.error("Failed to get daily budget used", e);
            return 0;
        }
    }

    public boolean canIssueToUser(String userId, String couponId, int maxPerUser) {
        String key = getUserIssueKey(userId, couponId);
        try {
            Long count = redisTemplate.opsForValue().increment(key);
            if (count != null && count > maxPerUser) {
                redisTemplate.opsForValue().decrement(key);
                log.warn("User {} has exceeded max issue limit for coupon {}", userId, couponId);
                return false;
            }
            if (count != null && count == 1) {
                redisTemplate.expire(key, 30, TimeUnit.DAYS);
            }
            return true;
        } catch (Exception e) {
            log.error("Failed to check user issue limit", e);
            return true;
        }
    }

    public void decrementUserIssueCount(String userId, String couponId) {
        String key = getUserIssueKey(userId, couponId);
        try {
            redisTemplate.opsForValue().decrement(key);
        } catch (Exception e) {
            log.error("Failed to decrement user issue count", e);
        }
    }

    public int getRemainingStock(String couponId) {
        return getStock(couponId);
    }

    public double getRemainingBudget() {
        return dailyBudget - getDailyBudgetUsed();
    }

    private String getStockKey(String couponId) {
        return STOCK_KEY_PREFIX + couponId;
    }

    private String getUserIssueKey(String userId, String couponId) {
        return USER_ISSUE_KEY_PREFIX + userId + ":" + couponId;
    }

    private String getDailyBudgetKey() {
        return DAILY_BUDGET_KEY + LocalDate.now().format(DATE_FORMATTER);
    }

    private String getDailyCouponCountKey() {
        return DAILY_COUPON_COUNT_KEY + LocalDate.now().format(DATE_FORMATTER);
    }
}

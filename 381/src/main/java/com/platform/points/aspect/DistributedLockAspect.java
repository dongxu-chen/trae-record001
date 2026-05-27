package com.platform.points.aspect;

import com.platform.points.annotation.DistributedLock;
import com.platform.points.exception.BusinessException;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.DefaultParameterNameDiscoverer;
import org.springframework.core.ParameterNameDiscoverer;
import org.springframework.expression.EvaluationContext;
import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;
import java.util.concurrent.TimeUnit;

@Slf4j
@Aspect
@Component
public class DistributedLockAspect {

    @Autowired
    private RedissonClient redissonClient;

    private final ExpressionParser parser = new SpelExpressionParser();
    private final ParameterNameDiscoverer nameDiscoverer = new DefaultParameterNameDiscoverer();

    @Around("@annotation(distributedLock)")
    public Object around(ProceedingJoinPoint joinPoint, DistributedLock distributedLock) throws Throwable {
        String lockKey = generateLockKey(joinPoint, distributedLock);
        RLock lock = redissonClient.getLock(lockKey);

        boolean acquired = false;
        long waitTime = distributedLock.waitTime();
        long leaseTime = distributedLock.leaseTime();
        boolean watchdog = distributedLock.watchdog();
        TimeUnit timeUnit = distributedLock.timeUnit();

        try {
            if (watchdog || leaseTime <= 0) {
                acquired = lock.tryLock(waitTime, timeUnit);
                log.info("获取分布式锁成功[看门狗模式], key: {}", lockKey);
            } else {
                acquired = lock.tryLock(waitTime, leaseTime, timeUnit);
                log.info("获取分布式锁成功[固定租约], key: {}, leaseTime: {}s", lockKey, leaseTime);
            }

            if (!acquired) {
                throw new BusinessException(distributedLock.message());
            }

            return joinPoint.proceed();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new BusinessException("获取分布式锁被中断");
        } finally {
            if (acquired && lock.isHeldByCurrentThread()) {
                lock.unlock();
                log.info("释放分布式锁成功, key: {}", lockKey);
            }
        }
    }

    private String generateLockKey(ProceedingJoinPoint joinPoint, DistributedLock distributedLock) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();
        String[] paramNames = nameDiscoverer.getParameterNames(method);
        Object[] args = joinPoint.getArgs();

        EvaluationContext context = new StandardEvaluationContext();
        if (paramNames != null) {
            for (int i = 0; i < paramNames.length; i++) {
                context.setVariable(paramNames[i], args[i]);
            }
        }

        Expression expression = parser.parseExpression(distributedLock.key());
        String keyValue = expression.getValue(context, String.class);
        return distributedLock.prefix() + keyValue;
    }
}

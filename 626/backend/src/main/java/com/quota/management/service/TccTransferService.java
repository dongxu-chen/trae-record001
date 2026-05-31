package com.quota.management.service;

import com.quota.management.algorithm.TokenBucket;
import com.quota.management.entity.TransferTransaction;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class TccTransferService {

    private static final String TRANSACTION_PREFIX = "quota:tcc:tx:";
    private static final String TRANSACTION_SET_KEY = "quota:tcc:tx:all";
    private static final String FROM_LOCK_PREFIX = "quota:tcc:lock:from:";
    private static final String TO_LOCK_PREFIX = "quota:tcc:lock:to:";
    private static final String FROZEN_PREFIX = "quota:tcc:frozen:";

    private final RedisTemplate<String, Object> redisTemplate;
    private final TokenBucketService tokenBucketService;

    @Value("${quota.tcc.timeout-seconds:60}")
    private long defaultTimeoutSeconds;

    @Value("${quota.tcc.lock-lease-seconds:30}")
    private long lockLeaseSeconds;

    public TransferTransaction tryPhase(String fromTenantId, String toTenantId, String granularity, long amount) {
        validateTenants(fromTenantId, toTenantId);

        String transactionId = UUID.randomUUID().toString().replace("-", "");

        String fromLockKey = FROM_LOCK_PREFIX + fromTenantId + ":" + granularity;
        String toLockKey = TO_LOCK_PREFIX + toTenantId + ":" + granularity;
        String fromLockValue = transactionId + ":from";
        String toLockValue = transactionId + ":to";

        boolean fromLocked = tryLock(fromLockKey, fromLockValue, lockLeaseSeconds);
        if (!fromLocked) {
            log.warn("TCC Try: Failed to lock from tenant: {}, granularity: {}", fromTenantId, granularity);
            throw new RuntimeException("源租户资源锁定失败，请稍后重试");
        }

        boolean toLocked = tryLock(toLockKey, toLockValue, lockLeaseSeconds);
        if (!toLocked) {
            unlock(fromLockKey, fromLockValue);
            log.warn("TCC Try: Failed to lock to tenant: {}, granularity: {}", toTenantId, granularity);
            throw new RuntimeException("目标租户资源锁定失败，请稍后重试");
        }

        try {
            TokenBucket fromBucket = tokenBucketService.getBucket(fromTenantId, granularity);
            TokenBucket toBucket = tokenBucketService.getBucket(toTenantId, granularity);

            if (fromBucket == null || toBucket == null) {
                throw new RuntimeException("租户令牌桶不存在");
            }

            long fromAvailable = fromBucket.getAvailableTokens();
            if (fromAvailable < amount) {
                throw new RuntimeException("源租户配额不足，可用: " + fromAvailable + "，需要: " + amount);
            }

            long fromVersionBefore = fromBucket.getVersion();
            long toVersionBefore = toBucket.getVersion();

            fromBucket.deductTokens(amount);
            tokenBucketService.saveBucket(fromBucket, granularity);

            String frozenKey = FROZEN_PREFIX + transactionId;
            FrozenResource frozen = FrozenResource.builder()
                    .transactionId(transactionId)
                    .fromTenantId(fromTenantId)
                    .toTenantId(toTenantId)
                    .granularity(granularity)
                    .amount(amount)
                    .fromVersionAfter(fromBucket.getVersion())
                    .toVersionBefore(toVersionBefore)
                    .build();
            redisTemplate.opsForValue().set(frozenKey, frozen, defaultTimeoutSeconds * 2, TimeUnit.SECONDS);

            TransferTransaction transaction = TransferTransaction.builder()
                    .transactionId(transactionId)
                    .fromTenantId(fromTenantId)
                    .toTenantId(toTenantId)
                    .granularity(granularity)
                    .amount(amount)
                    .status(TransferTransaction.TransactionStatus.TRYING)
                    .fromVersionBefore(fromVersionBefore)
                    .toVersionBefore(toVersionBefore)
                    .createdAt(LocalDateTime.now())
                    .timeoutSeconds(defaultTimeoutSeconds)
                    .build();

            String txKey = TRANSACTION_PREFIX + transactionId;
            redisTemplate.opsForValue().set(txKey, transaction, defaultTimeoutSeconds * 2, TimeUnit.SECONDS);
            redisTemplate.opsForSet().add(TRANSACTION_SET_KEY, transactionId);

            log.info("TCC Try: transactionId={}, from={}, to={}, granularity={}, amount={}, fromVersion={}->{}",
                    transactionId, fromTenantId, toTenantId, granularity, amount,
                    fromVersionBefore, fromBucket.getVersion());

            return transaction;

        } catch (Exception e) {
            unlock(fromLockKey, fromLockValue);
            unlock(toLockKey, toLockValue);
            throw e;
        }
    }

    public TransferTransaction confirmPhase(String transactionId) {
        TransferTransaction transaction = getTransaction(transactionId);
        if (transaction == null) {
            throw new RuntimeException("事务不存在: " + transactionId);
        }

        if (transaction.getStatus() != TransferTransaction.TransactionStatus.TRYING) {
            throw new RuntimeException("事务状态不正确，当前状态: " + transaction.getStatus());
        }

        String frozenKey = FROZEN_PREFIX + transactionId;
        Object frozenObj = redisTemplate.opsForValue().get(frozenKey);
        if (frozenObj == null) {
            transaction.setStatus(TransferTransaction.TransactionStatus.TIMED_OUT);
            saveTransaction(transaction);
            throw new RuntimeException("冻结资源已超时，事务自动回滚");
        }

        FrozenResource frozen = (FrozenResource) frozenObj;

        tokenBucketService.addTokens(transaction.getToTenantId(), transaction.getGranularity(), transaction.getAmount());

        redisTemplate.delete(frozenKey);

        transaction.setStatus(TransferTransaction.TransactionStatus.CONFIRMED);
        transaction.setConfirmedAt(LocalDateTime.now());
        saveTransaction(transaction);

        String fromLockKey = FROM_LOCK_PREFIX + transaction.getFromTenantId() + ":" + transaction.getGranularity();
        String toLockKey = TO_LOCK_PREFIX + transaction.getToTenantId() + ":" + transaction.getGranularity();
        unlock(fromLockKey, transactionId + ":from");
        unlock(toLockKey, transactionId + ":to");

        log.info("TCC Confirm: transactionId={}, from={}, to={}, amount={}",
                transactionId, transaction.getFromTenantId(), transaction.getToTenantId(), transaction.getAmount());

        return transaction;
    }

    public TransferTransaction cancelPhase(String transactionId) {
        TransferTransaction transaction = getTransaction(transactionId);
        if (transaction == null) {
            throw new RuntimeException("事务不存在: " + transactionId);
        }

        if (transaction.getStatus() != TransferTransaction.TransactionStatus.TRYING) {
            throw new RuntimeException("事务状态不正确，当前状态: " + transaction.getStatus());
        }

        String frozenKey = FROZEN_PREFIX + transactionId;
        Object frozenObj = redisTemplate.opsForValue().get(frozenKey);

        if (frozenObj != null) {
            FrozenResource frozen = (FrozenResource) frozenObj;
            tokenBucketService.addTokens(transaction.getFromTenantId(), transaction.getGranularity(), transaction.getAmount());
            redisTemplate.delete(frozenKey);
        }

        transaction.setStatus(TransferTransaction.TransactionStatus.CANCELLED);
        transaction.setCancelledAt(LocalDateTime.now());
        saveTransaction(transaction);

        String fromLockKey = FROM_LOCK_PREFIX + transaction.getFromTenantId() + ":" + transaction.getGranularity();
        String toLockKey = TO_LOCK_PREFIX + transaction.getToTenantId() + ":" + transaction.getGranularity();
        unlock(fromLockKey, transactionId + ":from");
        unlock(toLockKey, transactionId + ":to");

        log.info("TCC Cancel: transactionId={}, from={}, to={}, amount={}",
                transactionId, transaction.getFromTenantId(), transaction.getToTenantId(), transaction.getAmount());

        return transaction;
    }

    public TransferTransaction getTransaction(String transactionId) {
        String txKey = TRANSACTION_PREFIX + transactionId;
        Object obj = redisTemplate.opsForValue().get(txKey);
        if (obj instanceof TransferTransaction) {
            return (TransferTransaction) obj;
        }
        return null;
    }

    @Scheduled(fixedRate = 5000)
    public void cleanupTimedOutTransactions() {
        Set<Object> txIds = redisTemplate.opsForSet().members(TRANSACTION_SET_KEY);
        if (txIds == null || txIds.isEmpty()) {
            return;
        }

        for (Object txIdObj : txIds) {
            String txId = String.valueOf(txIdObj);
            TransferTransaction tx = getTransaction(txId);
            if (tx == null) {
                redisTemplate.opsForSet().remove(TRANSACTION_SET_KEY, txId);
                continue;
            }

            if (tx.getStatus() == TransferTransaction.TransactionStatus.TRYING) {
                LocalDateTime deadline = tx.getCreatedAt().plusSeconds(tx.getTimeoutSeconds());
                if (LocalDateTime.now().isAfter(deadline)) {
                    log.warn("TCC Timeout: auto-cancelling transaction {}", txId);
                    try {
                        cancelPhase(txId);
                    } catch (Exception e) {
                        log.error("Failed to auto-cancel transaction {}", txId, e);
                    }
                }
            }
        }
    }

    private void validateTenants(String fromTenantId, String toTenantId) {
        if (fromTenantId.equals(toTenantId)) {
            throw new RuntimeException("源租户和目标租户不能相同");
        }
    }

    private void saveTransaction(TransferTransaction transaction) {
        String txKey = TRANSACTION_PREFIX + transaction.getTransactionId();
        redisTemplate.opsForValue().set(txKey, transaction, transaction.getTimeoutSeconds() * 2, TimeUnit.SECONDS);
    }

    private boolean tryLock(String lockKey, String lockValue, long leaseTime) {
        Boolean result = redisTemplate.opsForValue()
                .setIfAbsent(lockKey, lockValue, leaseTime, TimeUnit.SECONDS);
        return Boolean.TRUE.equals(result);
    }

    private void unlock(String lockKey, String lockValue) {
        String luaScript = "if redis.call('get', KEYS[1]) == ARGV[1] then " +
                "return redis.call('del', KEYS[1]) " +
                "else " +
                "return 0 " +
                "end";
        org.springframework.data.redis.core.script.DefaultRedisScript<Long> redisScript =
                new org.springframework.data.redis.core.script.DefaultRedisScript<>(luaScript, Long.class);
        redisTemplate.execute(redisScript, java.util.Collections.singletonList(lockKey), lockValue);
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class FrozenResource implements java.io.Serializable {
        private static final long serialVersionUID = 1L;
        private String transactionId;
        private String fromTenantId;
        private String toTenantId;
        private String granularity;
        private long amount;
        private long fromVersionAfter;
        private long toVersionBefore;
    }
}

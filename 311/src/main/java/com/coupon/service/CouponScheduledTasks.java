package com.coupon.service;

import com.coupon.clickhouse.repository.CouponDistributionRepository;
import com.coupon.model.CouponDistribution;
import com.coupon.model.UserProfile;
import com.coupon.redis.service.UserProfileCacheService;
import com.coupon.rl.agent.DQNAgent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Component
public class CouponScheduledTasks {

    private final CouponDistributionService distributionService;
    private final CouponDistributionRepository distributionRepository;
    private final UserProfileCacheService userProfileCacheService;
    private final DQNAgent dqnAgent;

    public CouponScheduledTasks(CouponDistributionService distributionService,
                                CouponDistributionRepository distributionRepository,
                                UserProfileCacheService userProfileCacheService,
                                DQNAgent dqnAgent) {
        this.distributionService = distributionService;
        this.distributionRepository = distributionRepository;
        this.userProfileCacheService = userProfileCacheService;
        this.dqnAgent = dqnAgent;
    }

    @Scheduled(fixedRate = 60000)
    public void processExpiredCoupons() {
        log.debug("Starting process expired coupons task");
        LocalDateTime now = LocalDateTime.now();
        int processedCount = 0;

        try {
            List<CouponDistribution> potentiallyExpired =
                    distributionRepository.findPotentiallyExpired(1000);

            for (CouponDistribution distribution : potentiallyExpired) {
                if (distribution.getExpireTime() != null
                        && distribution.getExpireTime().isBefore(now)
                        && distribution.getStatus() == com.coupon.model.enums.CouponStatus.ISSUED) {
                    distributionService.expireCoupon(distribution.getDistributionId());
                    processedCount++;
                }
            }

            if (processedCount > 0) {
                log.info("Processed {} expired coupons", processedCount);
            }
        } catch (Exception e) {
            log.error("Failed to process expired coupons", e);
        }
    }

    @Scheduled(fixedRate = 30000, initialDelay = 10000)
    public void processRLLearningFromDistributions() {
        log.debug("Starting RL learning from processed distributions");

        try {
            List<CouponDistribution> distributions =
                    distributionRepository.findPendingForTraining(100);

            int trainedCount = 0;
            for (CouponDistribution distribution : distributions) {
                if (distribution.getRlActionIndex() != null) {
                    UserProfile profile = userProfileCacheService.getOrCreateDefault(distribution.getUserId());
                    dqnAgent.storeExperienceFromDistribution(distribution, profile, profile);
                    trainedCount++;
                }
            }

            if (trainedCount > 0) {
                log.info("Stored {} experiences for RL training", trainedCount);
            }

            dqnAgent.train();

        } catch (Exception e) {
            log.error("Failed to process RL learning", e);
        }
    }

    @Scheduled(cron = "0 0 1 * * ?")
    public void dailyStatisticsSummary() {
        log.info("Starting daily statistics summary task");
        try {
            log.info("RL Agent status - steps: {}, buffer: {}, epsilon: {}",
                    dqnAgent.getTrainStepCount(),
                    dqnAgent.getReplayBufferSize(),
                    dqnAgent.getEpsilon());

            dqnAgent.saveModel();
            log.info("Daily model checkpoint saved");

        } catch (Exception e) {
            log.error("Failed to run daily statistics summary", e);
        }
    }
}

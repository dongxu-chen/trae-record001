package com.sla.monitor.service;

import com.sla.monitor.model.SlaTier;
import com.sla.monitor.repository.SlaTierRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class SlaTierService {

    private static final Logger logger = LoggerFactory.getLogger(SlaTierService.class);

    private final SlaTierRepository slaTierRepository;

    public SlaTierService(SlaTierRepository slaTierRepository) {
        this.slaTierRepository = slaTierRepository;
    }

    public List<SlaTier> getAllTiers() {
        return slaTierRepository.findAll();
    }

    public List<SlaTier> getActiveTiers() {
        return slaTierRepository.findByActiveTrueOrderByPriorityLevelAsc();
    }

    public Optional<SlaTier> getTierById(Long id) {
        return slaTierRepository.findById(id);
    }

    public Optional<SlaTier> getTierByCode(String tierCode) {
        return slaTierRepository.findByTierCode(tierCode);
    }

    public SlaTier createTier(SlaTier tier) {
        if (slaTierRepository.existsByTierCode(tier.getTierCode())) {
            throw new IllegalArgumentException("Tier code already exists: " + tier.getTierCode());
        }
        if (slaTierRepository.existsByTierName(tier.getTierName())) {
            throw new IllegalArgumentException("Tier name already exists: " + tier.getTierName());
        }
        return slaTierRepository.save(tier);
    }

    public SlaTier updateTier(Long id, SlaTier tier) {
        return slaTierRepository.findById(id)
                .map(existing -> {
                    existing.setTierName(tier.getTierName());
                    existing.setDescription(tier.getDescription());
                    existing.setAvailabilityTarget(tier.getAvailabilityTarget());
                    existing.setLatencyTargetMs(tier.getLatencyTargetMs());
                    existing.setErrorRateTarget(tier.getErrorRateTarget());
                    existing.setMonthlyAvailabilityTarget(tier.getMonthlyAvailabilityTarget());
                    existing.setQuarterlyAvailabilityTarget(tier.getQuarterlyAvailabilityTarget());
                    existing.setPriorityLevel(tier.getPriorityLevel());
                    existing.setResponseTimeSla(tier.getResponseTimeSla());
                    existing.setResolutionTimeSla(tier.getResolutionTimeSla());
                    existing.setUptimeCreditPercent(tier.getUptimeCreditPercent());
                    existing.setActive(tier.isActive());
                    return slaTierRepository.save(existing);
                })
                .orElseThrow(() -> new IllegalArgumentException("Tier not found with id: " + id));
    }

    public void deleteTier(Long id) {
        slaTierRepository.deleteById(id);
    }

    public void initializeDefaultTiers() {
        if (slaTierRepository.count() == 0) {
            logger.info("Initializing default SLA tiers...");

            createTier(createTier(
                    SlaTier.TIER_PREMIUM, "尊享版",
                    99.99, 200.0, 0.1,
                    99.95, 99.99,
                    1, "15分钟", "1小时", 50.0
            ));

            createTier(createTier(
                    SlaTier.TIER_GOLD, "金牌",
                    99.95, 300.0, 0.5,
                    99.9, 99.95,
                    2, "30分钟", "2小时", 30.0
            ));

            createTier(createTier(
                    SlaTier.TIER_SILVER, "银牌",
                    99.9, 500.0, 1.0,
                    99.8, 99.9,
                    3, "1小时", "4小时", 20.0
            ));

            createTier(createTier(
                    SlaTier.TIER_BRONZE, "铜牌",
                    99.5, 800.0, 2.0,
                    99.0, 99.5,
                    4, "2小时", "8小时", 10.0
            ));

            createTier(createTier(
                    SlaTier.TIER_STANDARD, "标准版",
                    99.0, 1000.0, 3.0,
                    98.5, 99.0,
                    5, "4小时", "24小时", 5.0
            ));

            logger.info("Default SLA tiers initialized successfully");
        }
    }

    private SlaTier createTier(String code, String name,
                               double availability, double latency, double errorRate,
                               double monthly, double quarterly,
                               int priority, String responseTime, String resolutionTime,
                               double creditPercent) {
        SlaTier tier = new SlaTier();
        tier.setTierCode(code);
        tier.setTierName(name);
        tier.setDescription(name + "服务等级");
        tier.setAvailabilityTarget(availability);
        tier.setLatencyTargetMs(latency);
        tier.setErrorRateTarget(errorRate);
        tier.setMonthlyAvailabilityTarget(monthly);
        tier.setQuarterlyAvailabilityTarget(quarterly);
        tier.setPriorityLevel(priority);
        tier.setResponseTimeSla(responseTime);
        tier.setResolutionTimeSla(resolutionTime);
        tier.setUptimeCreditPercent(creditPercent);
        tier.setActive(true);
        return tier;
    }
}

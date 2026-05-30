package com.sla.monitor.config;

import com.sla.monitor.model.ServiceDependency;
import com.sla.monitor.model.ServiceInfo;
import com.sla.monitor.model.SlaTier;
import com.sla.monitor.repository.ServiceDependencyRepository;
import com.sla.monitor.repository.ServiceInfoRepository;
import com.sla.monitor.repository.SlaTierRepository;
import com.sla.monitor.service.DataGeneratorService;
import com.sla.monitor.service.RootCauseRuleMiningService;
import com.sla.monitor.service.SlaCalculationService;
import com.sla.monitor.service.SlaTierService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DataInitializer {

    private static final Logger logger = LoggerFactory.getLogger(DataInitializer.class);

    @Bean
    CommandLineRunner initDatabase(ServiceInfoRepository serviceRepository,
                                   SlaTierRepository slaTierRepository,
                                   ServiceDependencyRepository dependencyRepository,
                                   SlaTierService slaTierService,
                                   RootCauseRuleMiningService ruleMiningService,
                                   DataGeneratorService dataGeneratorService,
                                   SlaCalculationService slaCalculationService) {
        return args -> {
            slaTierService.initializeDefaultTiers();
            ruleMiningService.initializeDefaultRules();

            if (serviceRepository.count() == 0) {
                logger.info("Initializing service data with SLA tiers...");

                SlaTier goldTier = slaTierRepository.findByTierCode(SlaTier.TIER_GOLD).orElse(null);
                SlaTier silverTier = slaTierRepository.findByTierCode(SlaTier.TIER_SILVER).orElse(null);
                SlaTier premiumTier = slaTierRepository.findByTierCode(SlaTier.TIER_PREMIUM).orElse(null);
                SlaTier bronzeTier = slaTierRepository.findByTierCode(SlaTier.TIER_BRONZE).orElse(null);

                ServiceInfo userService = createServiceWithTier(
                        "user-service",
                        "User management and authentication service",
                        "http://user-service:8080",
                        goldTier
                );
                serviceRepository.save(userService);

                ServiceInfo orderService = createServiceWithTier(
                        "order-service",
                        "Order processing and management service",
                        "http://order-service:8080",
                        silverTier
                );
                serviceRepository.save(orderService);

                ServiceInfo paymentService = createServiceWithTier(
                        "payment-service",
                        "Payment processing and transaction service",
                        "http://payment-service:8080",
                        premiumTier
                );
                serviceRepository.save(paymentService);

                ServiceInfo inventoryService = createServiceWithTier(
                        "inventory-service",
                        "Inventory and stock management service",
                        "http://inventory-service:8080",
                        bronzeTier
                );
                serviceRepository.save(inventoryService);

                logger.info("Generated sample service data with SLA tiers");
                logger.info("  - payment-service: PREMIUM (99.99% available, 200ms latency)");
                logger.info("  - user-service: GOLD (99.95% available, 300ms latency)");
                logger.info("  - order-service: SILVER (99.9% available, 500ms latency)");
                logger.info("  - inventory-service: BRONZE (99.5% available, 800ms latency)");

                initializeServiceDependencies(dependencyRepository);

                dataGeneratorService.generateHistoricalData();
                slaCalculationService.calculateAndStoreMetrics();
                
                logger.info("Generated initial metrics data");
            }
        };
    }

    private void initializeServiceDependencies(ServiceDependencyRepository dependencyRepository) {
        logger.info("Initializing service dependencies...");

        ServiceDependency orderDependsOnUser = new ServiceDependency();
        orderDependsOnUser.setDownstreamService("order-service");
        orderDependsOnUser.setUpstreamService("user-service");
        orderDependsOnUser.setDependencyType(ServiceDependency.DependencyType.SYNCHRONOUS);
        orderDependsOnUser.setImpactLevel(ServiceDependency.ImpactLevel.HIGH);
        orderDependsOnUser.setDescription("Order service needs to validate user identity");
        orderDependsOnUser.setSlaImpactFactor(0.8);
        dependencyRepository.save(orderDependsOnUser);

        ServiceDependency paymentDependsOnOrder = new ServiceDependency();
        paymentDependsOnOrder.setDownstreamService("payment-service");
        paymentDependsOnOrder.setUpstreamService("order-service");
        paymentDependsOnOrder.setDependencyType(ServiceDependency.DependencyType.SYNCHRONOUS);
        paymentDependsOnOrder.setImpactLevel(ServiceDependency.ImpactLevel.CRITICAL);
        paymentDependsOnOrder.setDescription("Payment service processes orders created by order service");
        paymentDependsOnOrder.setSlaImpactFactor(1.0);
        dependencyRepository.save(paymentDependsOnOrder);

        ServiceDependency orderDependsOnInventory = new ServiceDependency();
        orderDependsOnInventory.setDownstreamService("order-service");
        orderDependsOnInventory.setUpstreamService("inventory-service");
        orderDependsOnInventory.setDependencyType(ServiceDependency.DependencyType.SYNCHRONOUS);
        orderDependsOnInventory.setImpactLevel(ServiceDependency.ImpactLevel.HIGH);
        orderDependsOnInventory.setDescription("Order service needs to check inventory availability");
        orderDependsOnInventory.setSlaImpactFactor(0.9);
        dependencyRepository.save(orderDependsOnInventory);

        ServiceDependency paymentDependsOnUser = new ServiceDependency();
        paymentDependsOnUser.setDownstreamService("payment-service");
        paymentDependsOnUser.setUpstreamService("user-service");
        paymentDependsOnUser.setDependencyType(ServiceDependency.DependencyType.SYNCHRONOUS);
        paymentDependsOnUser.setImpactLevel(ServiceDependency.ImpactLevel.MEDIUM);
        paymentDependsOnUser.setDescription("Payment service needs user account information");
        paymentDependsOnUser.setSlaImpactFactor(0.5);
        dependencyRepository.save(paymentDependsOnUser);

        logger.info("Initialized 4 service dependencies for SLA propagation analysis");
    }

    private ServiceInfo createServiceWithTier(String name, String description, String endpoint,
                                               SlaTier tier) {
        ServiceInfo service = new ServiceInfo();
        service.setServiceName(name);
        service.setDescription(description);
        service.setEndpoint(endpoint);
        service.setSlaTier(tier);
        service.setUseTierTargets(true);
        
        if (tier != null) {
            service.setAvailabilityTarget(tier.getAvailabilityTarget());
            service.setLatencyTargetMs(tier.getLatencyTargetMs());
            service.setErrorRateTarget(tier.getErrorRateTarget());
        } else {
            service.setAvailabilityTarget(99.9);
            service.setLatencyTargetMs(500.0);
            service.setErrorRateTarget(1.0);
        }
        
        service.setActive(true);
        return service;
    }
}

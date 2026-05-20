package com.configcenter.grayscale.repository;

import com.configcenter.common.repository.InMemoryRepository;
import com.configcenter.grayscale.entity.GrayscaleRule;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.stream.Collectors;

@Repository
public class GrayscaleRuleRepository extends InMemoryRepository<GrayscaleRule, String> {

    public List<GrayscaleRule> findByServiceName(String serviceName) {
        return storage.values().stream()
                .filter(rule -> serviceName.equals(rule.getServiceName()))
                .collect(Collectors.toList());
    }

    public List<GrayscaleRule> findByServiceNameAndStatus(String serviceName, GrayscaleRule.GrayscaleStatus status) {
        return storage.values().stream()
                .filter(rule -> serviceName.equals(rule.getServiceName()) && status == rule.getStatus())
                .collect(Collectors.toList());
    }

    public List<GrayscaleRule> findByStatus(GrayscaleRule.GrayscaleStatus status) {
        return storage.values().stream()
                .filter(rule -> status == rule.getStatus())
                .collect(Collectors.toList());
    }
}

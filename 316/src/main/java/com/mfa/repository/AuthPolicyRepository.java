package com.mfa.repository;

import com.mfa.entity.AuthPolicy;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface AuthPolicyRepository extends JpaRepository<AuthPolicy, Long> {

    Optional<AuthPolicy> findByName(String name);

    Optional<AuthPolicy> findByEnabledTrueAndRiskLevel(com.mfa.enums.RiskLevel riskLevel);
}

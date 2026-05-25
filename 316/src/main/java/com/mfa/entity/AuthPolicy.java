package com.mfa.entity;

import com.mfa.enums.FactorType;
import com.mfa.enums.PolicyOperator;
import com.mfa.enums.RiskLevel;
import jakarta.persistence.*;
import lombok.Data;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Entity
@Table(name = "auth_policies")
@EntityListeners(AuditingEntityListener.class)
public class AuthPolicy {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(length = 500)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PolicyOperator operator = PolicyOperator.AND;

    @Column
    private int minRequiredFactors = 2;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "policy_required_factors", joinColumns = @JoinColumn(name = "policy_id"))
    @Column(name = "factor_type")
    @Enumerated(EnumType.STRING)
    private List<FactorType> requiredFactors;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "policy_optional_factors", joinColumns = @JoinColumn(name = "policy_id"))
    @Column(name = "factor_type")
    @Enumerated(EnumType.STRING)
    private List<FactorType> optionalFactors;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RiskLevel riskLevel = RiskLevel.LOW;

    @Column
    private boolean adaptiveEnabled = false;

    @Column
    private int lowRiskRequiredFactors = 1;

    @Column
    private int mediumRiskRequiredFactors = 2;

    @Column
    private int highRiskRequiredFactors = 3;

    @Column
    private int criticalRiskRequiredFactors = 4;

    @Column
    private boolean stepUpEnabled = false;

    @Column
    private int sessionTimeoutMinutes = 30;

    @Column(nullable = false)
    private boolean enabled = true;

    @OneToMany(mappedBy = "authPolicy", fetch = FetchType.LAZY)
    private List<User> users;

    @CreatedDate
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(nullable = false)
    private LocalDateTime updatedAt;
}

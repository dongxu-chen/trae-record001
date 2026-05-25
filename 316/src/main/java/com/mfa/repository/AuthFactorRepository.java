package com.mfa.repository;

import com.mfa.entity.AuthFactor;
import com.mfa.enums.FactorType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AuthFactorRepository extends JpaRepository<AuthFactor, Long> {

    List<AuthFactor> findByUserIdAndEnabledTrue(Long userId);

    @Query("SELECT f FROM AuthFactor f WHERE f.user.id = :userId AND f.factorType = :factorType AND f.enabled = true")
    List<AuthFactor> findByUserIdAndFactorType(@Param("userId") Long userId, @Param("factorType") FactorType factorType);

    Optional<AuthFactor> findByCredentialId(String credentialId);

    @Query("SELECT f FROM AuthFactor f WHERE f.user.id = :userId AND f.verified = true AND f.enabled = true")
    List<AuthFactor> findVerifiedFactorsByUserId(@Param("userId") Long userId);

    @Query("SELECT f.factorType FROM AuthFactor f WHERE f.user.id = :userId AND f.verified = true AND f.enabled = true")
    List<FactorType> findVerifiedFactorTypesByUserId(@Param("userId") Long userId);
}

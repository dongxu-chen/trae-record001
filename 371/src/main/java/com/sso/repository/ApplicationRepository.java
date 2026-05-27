package com.sso.repository;

import com.sso.entity.Application;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ApplicationRepository extends JpaRepository<Application, Long> {

    Optional<Application> findByAppCode(String appCode);

    Optional<Application> findByClientId(String clientId);

    List<Application> findByEnabledTrueOrderBySortOrderAsc();

    List<Application> findByEnabledTrueAndVisibleInPortalTrueOrderBySortOrderAsc();

    @Query("SELECT a FROM Application a JOIN a.allowedRoles r WHERE r.name = :roleName AND a.enabled = true ORDER BY a.sortOrder ASC")
    List<Application> findByRoleName(String roleName);

    boolean existsByAppCode(String appCode);

    boolean existsByClientId(String clientId);
}

package com.configcenter.server.repository;

import com.configcenter.server.entity.ConfigDependency;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConfigDependencyRepository extends JpaRepository<ConfigDependency, Long> {

    List<ConfigDependency> findBySourceApplicationOrderByCreatedAtDesc(String sourceApplication);

    List<ConfigDependency> findByTargetApplicationOrderByCreatedAtDesc(String targetApplication);

    @Query("SELECT d FROM ConfigDependency d WHERE d.sourceApplication = :application " +
            "OR d.targetApplication = :application ORDER BY d.createdAt DESC")
    List<ConfigDependency> findByApplication(@Param("application") String application);

    @Query("SELECT d FROM ConfigDependency d WHERE d.sourceApplication = :sourceApp " +
            "AND d.sourceProfile = :sourceProfile " +
            "AND d.sourceLabel = :sourceLabel " +
            "AND d.sourceConfigKey = :sourceKey")
    List<ConfigDependency> findBySourceConfig(@Param("sourceApp") String sourceApp,
                                                @Param("sourceProfile") String sourceProfile,
                                                @Param("sourceLabel") String sourceLabel,
                                                @Param("sourceKey") String sourceKey);

    @Query("SELECT d FROM ConfigDependency d WHERE d.targetApplication = :targetApp " +
            "AND d.targetProfile = :targetProfile " +
            "AND d.targetLabel = :targetLabel " +
            "AND d.targetConfigKey = :targetKey")
    List<ConfigDependency> findByTargetConfig(@Param("targetApp") String targetApp,
                                                @Param("targetProfile") String targetProfile,
                                                @Param("targetLabel") String targetLabel,
                                                @Param("targetKey") String targetKey);

    Optional<ConfigDependency> findBySourceApplicationAndSourceProfileAndSourceLabelAndSourceConfigKeyAndTargetApplicationAndTargetProfileAndTargetLabelAndTargetConfigKey(
            String sourceApplication, String sourceProfile, String sourceLabel, String sourceConfigKey,
            String targetApplication, String targetProfile, String targetLabel, String targetConfigKey);
}

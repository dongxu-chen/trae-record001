package com.configcenter.server.repository;

import com.configcenter.server.entity.ConfigVersion;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConfigVersionRepository extends JpaRepository<ConfigVersion, Long> {

    List<ConfigVersion> findByApplicationAndProfileAndLabelOrderByCreatedAtDesc(
            String application, String profile, String label);

    List<ConfigVersion> findByApplicationOrderByCreatedAtDesc(String application);

    @Query("SELECT cv FROM ConfigVersion cv WHERE cv.application = :application " +
            "AND cv.profile = :profile AND cv.label = :label AND cv.status = 'PUBLISHED' " +
            "ORDER BY cv.createdAt DESC")
    List<ConfigVersion> findPublishedVersions(@Param("application") String application,
                                               @Param("profile") String profile,
                                               @Param("label") String label);

    @Query("SELECT cv FROM ConfigVersion cv WHERE cv.application = :application " +
            "AND cv.profile = :profile AND cv.label = :label " +
            "ORDER BY cv.createdAt DESC")
    List<ConfigVersion> findLatestVersion(@Param("application") String application,
                                           @Param("profile") String profile,
                                           @Param("label") String label);

    Optional<ConfigVersion> findByApplicationAndProfileAndLabelAndVersion(
            String application, String profile, String label, String version);

    @Query("SELECT COUNT(cv) > 0 FROM ConfigVersion cv WHERE cv.application = :application " +
            "AND cv.profile = :profile AND cv.label = :label AND cv.version = :version")
    boolean existsByVersion(@Param("application") String application,
                            @Param("profile") String profile,
                            @Param("label") String label,
                            @Param("version") String version);
}

package com.configcenter.server.repository;

import com.configcenter.server.entity.GrayRelease;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface GrayReleaseRepository extends JpaRepository<GrayRelease, Long> {

    List<GrayRelease> findByApplicationOrderByCreatedAtDesc(String application);

    List<GrayRelease> findByStatusOrderByCreatedAtDesc(GrayRelease.GrayStatus status);

    @Query("SELECT gr FROM GrayRelease gr WHERE gr.application = :application " +
            "AND gr.profile = :profile AND gr.label = :label AND gr.status = 'IN_GRAY'")
    Optional<GrayRelease> findActiveGrayRelease(@Param("application") String application,
                                                 @Param("profile") String profile,
                                                 @Param("label") String label);

    @Query("SELECT gr FROM GrayRelease gr WHERE gr.application = :application " +
            "AND gr.profile = :profile AND gr.label = :label " +
            "ORDER BY gr.createdAt DESC")
    List<GrayRelease> findByApplicationAndProfileAndLabel(
            @Param("application") String application,
            @Param("profile") String profile,
            @Param("label") String label);

    @Query("SELECT gr FROM GrayRelease gr WHERE gr.status IN ('PENDING_APPROVAL', 'IN_GRAY') " +
            "ORDER BY gr.createdAt DESC")
    List<GrayRelease> findActiveAndPendingGrayReleases();
}

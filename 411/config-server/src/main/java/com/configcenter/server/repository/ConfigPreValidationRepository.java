package com.configcenter.server.repository;

import com.configcenter.server.entity.ConfigPreValidation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConfigPreValidationRepository extends JpaRepository<ConfigPreValidation, Long> {

    List<ConfigPreValidation> findByApplicationOrderByStartTimeDesc(String application);

    List<ConfigPreValidation> findByApplicationAndProfileAndLabelOrderByStartTimeDesc(
            String application, String profile, String label);

    List<ConfigPreValidation> findByStatusOrderByStartTimeDesc(ConfigPreValidation.ValidationStatus status);

    @Query("SELECT pv FROM ConfigPreValidation pv WHERE pv.application = :application " +
            "AND pv.status IN ('PENDING', 'RUNNING') ORDER BY pv.startTime DESC")
    List<ConfigPreValidation> findActiveValidations(@Param("application") String application);

    Optional<ConfigPreValidation> findByApplicationAndProfileAndLabelAndVersion(
            String application, String profile, String label, String version);
}

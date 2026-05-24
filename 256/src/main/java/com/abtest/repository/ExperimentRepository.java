package com.abtest.repository;

import com.abtest.entity.Experiment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ExperimentRepository extends JpaRepository<Experiment, Long> {
    Optional<Experiment> findByName(String name);
    List<Experiment> findByStatus(Experiment.ExperimentStatus status);
    List<Experiment> findByOwner(String owner);
}

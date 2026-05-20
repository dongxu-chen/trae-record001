package com.risk.engine.repository;

import com.risk.engine.entity.MlModel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface MlModelRepository extends JpaRepository<MlModel, Long> {

    Optional<MlModel> findByModelCode(String modelCode);

    List<MlModel> findByStatus(String status);

    List<MlModel> findBySceneAndStatus(String scene, String status);

    List<MlModel> findByModelTypeAndStatus(String modelType, String status);
}

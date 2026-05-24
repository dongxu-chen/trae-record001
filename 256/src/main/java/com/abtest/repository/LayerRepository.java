package com.abtest.repository;

import com.abtest.entity.Layer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface LayerRepository extends JpaRepository<Layer, Long> {
    Optional<Layer> findByName(String name);
    List<Layer> findByIsActiveTrue();
}

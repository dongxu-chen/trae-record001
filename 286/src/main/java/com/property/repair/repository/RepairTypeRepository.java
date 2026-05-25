package com.property.repair.repository;

import com.property.repair.entity.RepairType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RepairTypeRepository extends JpaRepository<RepairType, Long> {

    List<RepairType> findByStatus(Integer status);
}

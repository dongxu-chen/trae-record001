package com.smartschedule.repository;

import com.smartschedule.entity.ShiftType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ShiftTypeRepository extends JpaRepository<ShiftType, Long> {
    Optional<ShiftType> findByCode(String code);
    List<ShiftType> findByIsActiveTrue();
}

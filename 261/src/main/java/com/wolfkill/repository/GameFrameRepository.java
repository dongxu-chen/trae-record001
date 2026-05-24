package com.wolfkill.repository;

import com.wolfkill.entity.GameFrame;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface GameFrameRepository extends JpaRepository<GameFrame, Long> {
    List<GameFrame> findByRecordIdOrderByFrameIndexAsc(Long recordId);
}

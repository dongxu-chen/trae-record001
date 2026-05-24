package com.wolfkill.repository;

import com.wolfkill.entity.GameRoom;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface GameRoomRepository extends JpaRepository<GameRoom, Long> {
    Page<GameRoom> findByActiveTrue(Pageable pageable);
    List<GameRoom> findByActiveTrue();
}

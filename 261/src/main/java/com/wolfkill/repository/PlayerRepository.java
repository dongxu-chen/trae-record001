package com.wolfkill.repository;

import com.wolfkill.entity.Player;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface PlayerRepository extends JpaRepository<Player, Long> {
    Optional<Player> findByNickname(String nickname);
    Optional<Player> findBySessionId(String sessionId);
}

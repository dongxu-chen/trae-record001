package com.sso.repository;

import com.sso.entity.UserSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface UserSessionRepository extends JpaRepository<UserSession, Long> {

    Optional<UserSession> findBySessionId(String sessionId);

    List<UserSession> findByUserIdAndActiveTrue(Long userId);

    List<UserSession> findByUsernameAndActiveTrue(String username);

    @Modifying
    @Query("UPDATE UserSession s SET s.active = false WHERE s.sessionId = :sessionId")
    void invalidateSession(@Param("sessionId") String sessionId);

    @Modifying
    @Query("UPDATE UserSession s SET s.active = false WHERE s.userId = :userId AND s.active = true")
    void invalidateAllSessionsForUser(@Param("userId") Long userId);

    @Modifying
    @Query("UPDATE UserSession s SET s.active = false WHERE s.expiresAt < :now AND s.active = true")
    void invalidateExpiredSessions(@Param("now") LocalDateTime now);

    @Modifying
    @Query("UPDATE UserSession s SET s.lastActive = :lastActive WHERE s.sessionId = :sessionId")
    void updateLastActive(@Param("sessionId") String sessionId, @Param("lastActive") LocalDateTime lastActive);
}

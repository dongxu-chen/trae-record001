package com.sso.repository;

import com.sso.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByUsername(String username);

    Optional<User> findByEmail(String email);

    Optional<User> findByLdapDn(String ldapDn);

    boolean existsByUsername(String username);

    boolean existsByEmail(String email);

    @Modifying
    @Query("UPDATE User u SET u.failedAttempts = u.failedAttempts + 1 WHERE u.username = :username")
    void incrementFailedAttempts(@Param("username") String username);

    @Modifying
    @Query("UPDATE User u SET u.failedAttempts = 0 WHERE u.username = :username")
    void resetFailedAttempts(@Param("username") String username);

    @Modifying
    @Query("UPDATE User u SET u.lockUntil = :lockUntil, u.accountNonLocked = false WHERE u.username = :username")
    void lockAccount(@Param("username") String username, @Param("lockUntil") LocalDateTime lockUntil);

    @Modifying
    @Query("UPDATE User u SET u.lastLogin = :lastLogin, u.lastLoginIp = :lastLoginIp WHERE u.username = :username")
    void updateLastLogin(@Param("username") String username, @Param("lastLogin") LocalDateTime lastLogin, @Param("lastLoginIp") String lastLoginIp);
}

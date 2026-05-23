package com.shortlink.repository;

import com.shortlink.entity.ShortLink;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

@Repository
public interface ShortLinkRepository extends JpaRepository<ShortLink, Long> {

    Optional<ShortLink> findByShortCode(String shortCode);

    Optional<ShortLink> findByOriginUrl(String originUrl);

    boolean existsByShortCode(String shortCode);

    @Modifying
    @Transactional
    @Query("UPDATE ShortLink s SET s.pvCount = s.pvCount + 1 WHERE s.shortCode = :shortCode")
    void incrementPvCount(String shortCode);

    @Modifying
    @Transactional
    @Query("UPDATE ShortLink s SET s.uvCount = s.uvCount + 1 WHERE s.shortCode = :shortCode")
    void incrementUvCount(String shortCode);

    @Modifying
    @Transactional
    @Query("DELETE FROM ShortLink s WHERE s.expireTime < :now AND s.expireTime IS NOT NULL")
    int deleteExpiredLinks(LocalDateTime now);
}

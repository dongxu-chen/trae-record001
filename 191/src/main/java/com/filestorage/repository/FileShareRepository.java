package com.filestorage.repository;

import com.filestorage.entity.FileShare;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

@Repository
public interface FileShareRepository extends JpaRepository<FileShare, Long> {
    Optional<FileShare> findByShareCode(String shareCode);
    Page<FileShare> findByTenantIdAndStatus(Long tenantId, Integer status, Pageable pageable);

    @Modifying
    @Transactional
    @Query("UPDATE FileShare f SET f.status = 0 WHERE f.expireAt < :now AND f.status = 1")
    int expireShares(LocalDateTime now);
}
